from cProfile import Profile
from dataclasses import fields
from rest_framework import serializers
from api import models
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q


class ChoicesField(serializers.Field):
    def __init__(self, choices, **kwargs):
        self._choices = choices
        super(ChoicesField, self).__init__(**kwargs)

    def to_representation(self, obj):
        if obj in self._choices:
            return self._choices[obj]
        return obj

    def to_internal_value(self, data):
        if data in self._choices:
            return getattr(self._choices, data)
        raise serializers.ValidationError(["choice not valid"])


# -------------------------- MODELS SERIALIZERS ----------------------------
class PhotoSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(
        required=True, allow_null=False, max_length=None, use_url=True
    )

    class Meta:
        model = models.Photo
        fields = ["id", "image", "profile"]


class ProfileSerializer(serializers.ModelSerializer):
    token = serializers.SerializerMethodField(read_only=True)

    # transform the gender and show me into text "Male"
    gender = serializers.CharField(
        source="get_gender_display", required=True, allow_null=False
    )
    show_me = serializers.CharField(
        source="get_show_me_display", required=True, allow_null=False
    )

    photos = PhotoSerializer(source="photo_set", many=True, read_only=True)

    is_in_group = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()
    total_matches = serializers.SerializerMethodField()

    class Meta:
        model = models.Profile
        exclude = [
            "user_permissions",
            "groups",
            "password",
            "last_login",
            "is_staff",
            "is_active",
        ]

    # refresh the token everytime the user is called
    def get_token(self, obj):
        token = RefreshToken.for_user(obj)
        return str(token.access_token)

    def get_is_in_group(self, profile):
        return profile.member_group.all().exists()

    def get_total_likes(self, profile):
        matches = matches = models.Match.objects.filter(
            Q(profile1=profile.id) | Q(profile2=profile.id)
        )
        matched_profiles = [match.profile1.id for match in matches] + [
            match.profile2.id for match in matches
        ]
        likes = profile.likes.exclude(id__in=matched_profiles)
        count = likes.count()
        return count

    def get_total_matches(self, profile):
        matches = matches = models.Match.objects.filter(
            Q(profile1=profile.id) | Q(profile2=profile.id)
        )
        count = matches.count()
        return count


# -------------------------- SWIPE SERIALIZERS -----------------------------
class SwipeProfileSerializer(serializers.ModelSerializer):
    is_in_group = serializers.SerializerMethodField()
    gender = serializers.CharField(
        source="get_gender_display", required=True, allow_null=False
    )
    show_me = serializers.CharField(
        source="get_show_me_display", required=True, allow_null=False
    )

    photos = PhotoSerializer(source="photo_set", many=True, read_only=True)

    class Meta:
        model = models.Profile
        fields = [
            "id",
            "email",
            "is_in_group",
            "name",
            "birthdate",
            "age",
            "gender",
            "show_me",
            "nationality",
            "city",
            "university",
            "description",
            "location",
            "photos",
            "instagram",
        ]

    def get_is_in_group(self, profile):
        return profile.member_group.all().exists()


""" 
    Swipe group serializer show a owner property and show 
    all the members (including the owner) in the members property 
"""


class SwipeGroupSerializer(serializers.ModelSerializer):
    total_members = serializers.SerializerMethodField()
    owner = SwipeProfileSerializer(read_only=True, many=False)
    members = SwipeProfileSerializer(read_only=True, many=True)
    gender = serializers.CharField(
        source="get_gender_display", required=False, allow_null=False
    )

    class Meta:
        model = models.Group
        fields = ["id", "gender", "total_members", "created_at", "owner", "members"]

    def get_total_members(self, group):
        return group.members.count()


# -------------------------- GROUP SERIALIZERS --------------------------------
class GroupSerializer(serializers.ModelSerializer):
    total_members = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    owner = SwipeProfileSerializer(read_only=True, many=False)
    gender = ChoicesField(
        choices=models.Group.GENDER_CHOICES,
        required=False,
        allow_null=False,
    )

    class Meta:
        model = models.Group
        fields = "__all__"

    def get_members(self, group):
        # get the group
        group = models.Group.objects.get(pk=group.id)
        # filter the members and exclude the owner
        members_without_owner = group.members.exclude(id=group.owner.id)
        # serialize the members
        serializer = SwipeProfileSerializer(instance=members_without_owner, many=True)
        return serializer.data

    def get_total_members(self, group):
        return group.members.count()


class GroupSerializerWithLink(GroupSerializer):
    share_link = serializers.CharField(required=True, allow_null=False)


# -------------------------- BLOCKED PROFILES SERIALIZERS --------------------------------
class MatchSerializer(serializers.ModelSerializer):
    profile1 = SwipeProfileSerializer(read_only=True, many=False)
    profile2 = SwipeProfileSerializer(read_only=True, many=False)

    class Meta:
        model = models.Match
        fields = ["id", "profile1", "profile2"]


# -------------------------- DATA ACTIONS SERIALIZERS -----------------------------
class CreateProfileSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, allow_null=False)
    birthdate = serializers.DateField(required=True, allow_null=False)
    university = serializers.CharField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_null=True)
    gender = ChoicesField(
        choices=models.Profile.GENDER_CHOICES,
        required=False,
        allow_null=False,
    )
    show_me = ChoicesField(
        choices=models.Profile.SHOW_ME_CHOICES,
        required=False,
        allow_null=False,
    )


class UpdateProfileSerializer(serializers.Serializer):
    instagram = serializers.CharField(required=False, allow_null=True)
    nationality = serializers.CharField(required=False, allow_null=True)
    city = serializers.CharField(required=False, allow_null=True)
    university = serializers.CharField(required=False, allow_null=True)
    description = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    gender = ChoicesField(
        choices=models.Profile.GENDER_CHOICES,
        required=False,
        allow_null=False,
    )
    show_me = ChoicesField(
        choices=models.Profile.SHOW_ME_CHOICES,
        required=False,
        allow_null=False,
    )


class UpdateLocation(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class GroupSerializerWithMember(serializers.Serializer):
    member_id = serializers.CharField(required=True, allow_null=False)
