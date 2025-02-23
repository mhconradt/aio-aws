# Copyright 2019-2022 Darren Weber
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict

import boto3
import botocore.exceptions
import pytest
from pytest_aiomoto.aws_s3 import assert_bucket_200
from pytest_aiomoto.aws_s3 import assert_object_200

from aio_aws.s3_io import YamlBaseModel
from aio_aws.s3_io import geojson_s3_dump
from aio_aws.s3_io import geojson_s3_load
from aio_aws.s3_io import geojsons_dump
from aio_aws.s3_io import geojsons_s3_dump
from aio_aws.s3_io import geojsons_s3_load
from aio_aws.s3_io import get_s3_content
from aio_aws.s3_io import json_s3_dump
from aio_aws.s3_io import json_s3_load
from aio_aws.s3_io import s3_file_info
from aio_aws.s3_io import s3_file_wait
from aio_aws.s3_io import s3_files_info
from aio_aws.s3_io import yaml_s3_dump
from aio_aws.s3_io import yaml_s3_load
from aio_aws.s3_uri import S3URI
from aio_aws.s3_uri import S3Info


def test_s3_file_info(aws_s3_client, s3_uri_object, s3_object_text, mocker):
    assert_bucket_200(s3_uri_object.bucket, aws_s3_client)
    assert_object_200(s3_uri_object.bucket, s3_uri_object.key, aws_s3_client)
    spy_client = mocker.spy(boto3, "client")
    spy_resource = mocker.spy(boto3, "resource")
    s3_info = s3_file_info(s3_uri_object.s3_uri)
    assert isinstance(s3_info, S3Info)
    s3_dict = s3_info.dict()
    assert isinstance(s3_dict, Dict)
    assert s3_dict["s3_uri"] == s3_uri_object.s3_uri
    assert s3_dict["s3_size"] == len(s3_object_text)
    # last-modified is an iso8601 string
    assert isinstance(s3_dict["last_modified"], str)
    last_modified = datetime.fromisoformat(s3_dict["last_modified"])
    assert isinstance(last_modified, datetime)
    # test the JSON representation
    s3_json = s3_info.json()
    assert s3_json == json.dumps(s3_dict)
    # the s3 client is used once to get the s3 object data
    assert spy_client.call_count == 1
    assert spy_resource.call_count == 0


def test_s3_files_info(aws_s3_client, s3_uri_object, s3_object_text, mocker):
    assert_bucket_200(s3_uri_object.bucket, aws_s3_client)
    assert_object_200(s3_uri_object.bucket, s3_uri_object.key, aws_s3_client)
    spy_client = mocker.spy(boto3, "client")
    spy_resource = mocker.spy(boto3, "resource")
    s3_files = s3_files_info([s3_uri_object.s3_uri])
    for s3_info in s3_files:
        assert isinstance(s3_info, S3Info)
    # the s3 client is used once to get the s3 object data
    assert spy_client.call_count == 1
    assert spy_resource.call_count == 0


def test_s3_file_wait(aws_s3_client, s3_uri_object, s3_object_text, mocker):
    assert_bucket_200(s3_uri_object.bucket, aws_s3_client)
    assert_object_200(s3_uri_object.bucket, s3_uri_object.key, aws_s3_client)
    spy_client = mocker.spy(boto3, "client")
    spy_resource = mocker.spy(boto3, "resource")
    s3_uri = s3_file_wait(s3_uri_object.s3_uri, delay=1, max_attempts=10)
    assert isinstance(s3_uri, S3URI)
    # the s3 client is used once to get the s3 object data
    assert spy_client.call_count == 1
    assert spy_resource.call_count == 0


def test_s3_file_wait_404(aws_s3_client, mocker):
    spy_client = mocker.spy(boto3, "client")
    spy_resource = mocker.spy(boto3, "resource")
    with pytest.raises(
        botocore.exceptions.WaiterError, match="Waiter ObjectExists failed"
    ):
        s3_file_wait("s3://bucket/key", delay=0.2, max_attempts=2)
    # the s3 client is used once to get the s3 object data
    assert spy_client.call_count == 1
    assert spy_resource.call_count == 0


def test_get_s3_content(aws_s3_client, s3_uri_object, s3_object_text, mocker):
    assert_bucket_200(s3_uri_object.bucket, aws_s3_client)
    assert_object_200(s3_uri_object.bucket, s3_uri_object.key, aws_s3_client)
    spy_client = mocker.spy(boto3, "client")
    spy_resource = mocker.spy(boto3, "resource")
    object_data = get_s3_content(s3_uri_object.s3_uri)
    assert object_data == s3_object_text
    # the s3 client is used once to get the s3 object data
    assert spy_client.call_count == 1
    assert spy_resource.call_count == 0


def test_geojson_io(geojson_feature_collection, aws_s3_client, s3_bucket, mocker):
    assert_bucket_200(s3_bucket, aws_s3_client)
    spy_client = mocker.spy(boto3, "client")
    spy_resource = mocker.spy(boto3, "resource")
    s3_uri = S3URI(f"s3://{s3_bucket}/tmp.geojson")
    result = geojson_s3_dump(geojson_feature_collection, s3_uri.s3_uri)
    assert result == s3_uri.s3_uri
    # the s3 client is used once to upload the s3 object data
    assert spy_client.call_count == 1
    assert spy_resource.call_count == 0
    assert_object_200(bucket=s3_bucket, key=s3_uri.key, s3_client=aws_s3_client)
    data = geojson_s3_load(s3_uri.s3_uri)
    assert data == geojson_feature_collection
    # the s3 client is used to read the s3 object data
    assert spy_client.call_count == 2
    assert spy_resource.call_count == 0


def test_geojsons_io(geojson_features, aws_s3_client, s3_bucket, mocker):
    assert_bucket_200(s3_bucket, aws_s3_client)
    spy_client = mocker.spy(boto3, "client")
    spy_resource = mocker.spy(boto3, "resource")
    s3_uri = S3URI(f"s3://{s3_bucket}/tmp.geojsons")
    result = geojsons_s3_dump(geojson_features, s3_uri.s3_uri)
    assert result == s3_uri.s3_uri
    # the s3 client is used once to upload the s3 object data
    assert spy_client.call_count == 1
    assert spy_resource.call_count == 0
    assert_object_200(bucket=s3_bucket, key=s3_uri.key, s3_client=aws_s3_client)
    data = geojsons_s3_load(s3_uri.s3_uri)
    assert data == geojson_features
    # the s3 client is used to read the s3 object data
    assert spy_client.call_count == 2
    assert spy_resource.call_count == 0


def test_geojsons_dump(geojson_features):
    with tempfile.NamedTemporaryFile() as tmp_file:
        tmp_path = Path(tmp_file.name)
        dump_path = geojsons_dump(geojson_features, tmp_path)
        assert dump_path == tmp_path
        assert tmp_path.exists()


def test_json_io(geojson_feature_collection, aws_s3_client, s3_bucket, mocker):
    assert_bucket_200(s3_bucket, aws_s3_client)
    spy_client = mocker.spy(boto3, "client")
    spy_resource = mocker.spy(boto3, "resource")
    s3_uri = S3URI(f"s3://{s3_bucket}/tmp.json")
    result = json_s3_dump(geojson_feature_collection, s3_uri.s3_uri)
    assert result == s3_uri.s3_uri
    # the s3 client is used once to upload the s3 object data
    assert spy_client.call_count == 1
    assert spy_resource.call_count == 0
    assert_object_200(bucket=s3_bucket, key=s3_uri.key, s3_client=aws_s3_client)
    data = json_s3_load(s3_uri.s3_uri)
    assert data == geojson_feature_collection
    # the s3 client is used to read the s3 object data
    assert spy_client.call_count == 2
    assert spy_resource.call_count == 0


def test_yaml_io(geojson_feature_collection, aws_s3_client, s3_bucket, mocker):
    # Since JSON is a subset of YAML, this should work for GeoJSON data
    assert_bucket_200(s3_bucket, aws_s3_client)
    spy_client = mocker.spy(boto3, "client")
    spy_resource = mocker.spy(boto3, "resource")
    s3_uri = S3URI(f"s3://{s3_bucket}/tmp.yaml")
    result = yaml_s3_dump(geojson_feature_collection, s3_uri.s3_uri)
    assert result == s3_uri.s3_uri
    # the s3 client is used once to upload the s3 object data
    assert spy_client.call_count == 1
    assert spy_resource.call_count == 0
    assert_object_200(bucket=s3_bucket, key=s3_uri.key, s3_client=aws_s3_client)
    data = yaml_s3_load(s3_uri.s3_uri)
    assert data == geojson_feature_collection
    # the s3 client is used to read the s3 object data
    assert spy_client.call_count == 2
    assert spy_resource.call_count == 0


class GeoJsonModel(YamlBaseModel):
    feature_collection: Dict


def test_json_base_model_file_io(geojson_feature_collection):
    model = GeoJsonModel(feature_collection=geojson_feature_collection)
    with tempfile.NamedTemporaryFile(suffix=".json") as tmp_file:
        json_file = Path(tmp_file.name)
        result = model.json_dump(json_file)
        assert result == json_file
        assert json_file.exists() and json_file.stat().st_size > 0
        model_loaded = GeoJsonModel.load(json_file)
        assert model_loaded.feature_collection == geojson_feature_collection


def test_yaml_base_model_file_io(geojson_feature_collection):
    # Since JSON is a subset of YAML, this should work for GeoJSON data
    model = GeoJsonModel(feature_collection=geojson_feature_collection)
    with tempfile.NamedTemporaryFile(suffix=".yaml") as tmp_file:
        yaml_file = Path(tmp_file.name)
        result = model.yaml_dump(yaml_file)
        assert result == yaml_file
        assert yaml_file.exists() and yaml_file.stat().st_size > 0
        model_loaded = GeoJsonModel.load(yaml_file)
        assert model_loaded.feature_collection == geojson_feature_collection


def test_json_base_model_s3_io(
    geojson_feature_collection, aws_s3_client, s3_bucket, mocker
):
    assert_bucket_200(s3_bucket, aws_s3_client)
    spy_client = mocker.spy(boto3, "client")
    spy_resource = mocker.spy(boto3, "resource")
    s3_uri = S3URI(f"s3://{s3_bucket}/tmp.json")

    model = GeoJsonModel(feature_collection=geojson_feature_collection)
    result = model.json_s3_dump(s3_uri)
    assert result == s3_uri
    # the s3 client is used once to upload the s3 object data
    assert spy_client.call_count == 1
    assert spy_resource.call_count == 0
    assert_object_200(bucket=s3_bucket, key=s3_uri.key, s3_client=aws_s3_client)

    model_loaded = GeoJsonModel.load(s3_uri)
    assert model_loaded.feature_collection == geojson_feature_collection
    # the s3 client is used to read the s3 object data
    assert spy_client.call_count == 2
    assert spy_resource.call_count == 0


def test_yaml_base_model_s3_io(
    geojson_feature_collection, aws_s3_client, s3_bucket, mocker
):
    # Since JSON is a subset of YAML, this should work for GeoJSON data
    assert_bucket_200(s3_bucket, aws_s3_client)
    spy_client = mocker.spy(boto3, "client")
    spy_resource = mocker.spy(boto3, "resource")
    s3_uri = S3URI(f"s3://{s3_bucket}/tmp.yaml")

    model = GeoJsonModel(feature_collection=geojson_feature_collection)
    result = model.yaml_s3_dump(s3_uri)
    assert result == s3_uri
    # the s3 client is used once to upload the s3 object data
    assert spy_client.call_count == 1
    assert spy_resource.call_count == 0
    assert_object_200(bucket=s3_bucket, key=s3_uri.key, s3_client=aws_s3_client)

    model_loaded = GeoJsonModel.load(s3_uri)
    assert model_loaded.feature_collection == geojson_feature_collection
    # the s3 client is used to read the s3 object data
    assert spy_client.call_count == 2
    assert spy_resource.call_count == 0
