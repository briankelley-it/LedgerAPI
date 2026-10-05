"""Serializers used only to describe responses in the OpenAPI schema."""

from rest_framework import serializers


class ErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(allow_null=True)


class ErrorSerializer(serializers.Serializer):
    error = ErrorBodySerializer()


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    database = serializers.CharField()
