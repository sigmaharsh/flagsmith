from django.db.models.signals import post_init, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from environments.tasks import rebuild_environment_document
from features.versioning.models import EnvironmentFeatureVersion


@receiver(post_save, sender=EnvironmentFeatureVersion)
def add_existing_feature_states(
    instance: EnvironmentFeatureVersion, created: bool, **kwargs
):
    if not created:
        return

    previous_environment_feature_version = instance.get_previous_version()
    if not previous_environment_feature_version:
        return

    for feature_state in previous_environment_feature_version.feature_states.all():
        feature_state.clone(
            env=instance.environment, environment_feature_version=instance
        )


@receiver(pre_save, sender=EnvironmentFeatureVersion)
def update_live_from(instance: EnvironmentFeatureVersion, **kwargs):
    if instance.published and not instance.live_from:
        instance.live_from = timezone.now()


@receiver(post_init, sender=EnvironmentFeatureVersion)
def cache_fields(instance: EnvironmentFeatureVersion, **kwargs):
    instance._init_fields = {"published": instance.published}


@receiver(post_save, sender=EnvironmentFeatureVersion)
def update_environment_document(instance: EnvironmentFeatureVersion, **kwargs):
    init_fields = getattr(instance, "_init_fields", dict())
    if instance.published and init_fields.get("published") is not True:
        rebuild_environment_document.delay(
            kwargs={"environment_id": instance.environment_id},
            delay_until=instance.live_from,
        )
