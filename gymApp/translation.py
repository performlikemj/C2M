from modeltranslation.translator import translator, TranslationOptions
from .models import Profile, GymVisit, MembershipType, Membership, PersonalTrainingSession, PurchasedTrainingSession, TrialPayment

class ProfileTranslationOptions(TranslationOptions):
    fields = ()

class GymVisitTranslationOptions(TranslationOptions):
    fields = ()

class MembershipTypeTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

class MembershipTranslationOptions(TranslationOptions):
    fields = ()

class PersonalTrainingSessionTranslationOptions(TranslationOptions):
    fields = ()

class PurchasedTrainingSessionTranslationOptions(TranslationOptions):
    fields = ()

class TrialPaymentTranslationOptions(TranslationOptions):
    fields = ()

translator.register(Profile, ProfileTranslationOptions)
translator.register(GymVisit, GymVisitTranslationOptions)
translator.register(MembershipType, MembershipTypeTranslationOptions)
translator.register(Membership, MembershipTranslationOptions)
translator.register(PersonalTrainingSession, PersonalTrainingSessionTranslationOptions)
translator.register(PurchasedTrainingSession, PurchasedTrainingSessionTranslationOptions)
translator.register(TrialPayment, TrialPaymentTranslationOptions)