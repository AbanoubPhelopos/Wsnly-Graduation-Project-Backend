from rest_framework import serializers


class CoordinateSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class TextRouteRequestSerializer(serializers.Serializer):
    text = serializers.CharField()


class MapRouteRequestSerializer(serializers.Serializer):
    origin = CoordinateSerializer()
    destination = CoordinateSerializer()


class RoutePointSerializer(serializers.Serializer):
    name = serializers.CharField(allow_null=True, required=False)
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class RouteStepLocationSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class RouteStepSerializer(serializers.Serializer):
    instruction = serializers.CharField()
    distance_meters = serializers.FloatField()
    duration_seconds = serializers.FloatField()
    type = serializers.CharField()
    line_name = serializers.CharField(allow_blank=True)
    start_location = RouteStepLocationSerializer()
    end_location = RouteStepLocationSerializer()


class RouteBodySerializer(serializers.Serializer):
    total_distance_meters = serializers.FloatField()
    total_duration_seconds = serializers.FloatField()
    steps = RouteStepSerializer(many=True)


class RouteMetaSerializer(serializers.Serializer):
    intent = serializers.CharField()
    step_count = serializers.IntegerField()


class ErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()


class RouteErrorResponseSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    error = ErrorBodySerializer()


class RegisterRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    mobile_number = serializers.CharField()
    gender = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    role = serializers.CharField(required=False)


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class GoogleLoginRequestSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class AuthUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class AuthSuccessResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = AuthUserSerializer()


class ValidationErrorsResponseSerializer(serializers.Serializer):
    errors = serializers.ListField(child=serializers.DictField())
