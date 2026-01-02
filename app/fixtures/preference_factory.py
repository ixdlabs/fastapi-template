import factory

from app.features.preferences.models.preference import Preference


class PreferenceFactory(factory.Factory[Preference]):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = Preference

    key = factory.Faker("word")
    value = factory.Faker("sentence", nb_words=4)
    is_global = True
