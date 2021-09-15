# Copyright 2019-2021 Darren Weber
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

"""
Test Aio AWS Batch DB
"""
import asyncio
from typing import Dict
from typing import List
from typing import Set

import pytest

from aio_aws.aio_aws_batch import aio_find_complete_jobs
from aio_aws.aio_aws_batch import aio_find_jobs_by_status
from aio_aws.aio_aws_batch import aio_find_running_jobs
from aio_aws.aio_aws_batch import find_complete_jobs
from aio_aws.aio_aws_batch import find_jobs_by_status
from aio_aws.aio_aws_batch import find_running_jobs
from aio_aws.aio_aws_batch_db import AioAWSBatchDB
from aio_aws.aio_aws_batch_db import AioAWSBatchRedisDB
from aio_aws.aio_aws_batch_db import AioAWSBatchTinyDB
from aio_aws.aws_batch_models import AWSBatchJob


@pytest.fixture
def aiotiny_jobs_db(tmp_path) -> AioAWSBatchDB:
    jobs_db_file = str(tmp_path / "test_batch_jobs_db.json")
    logs_db_file = str(tmp_path / "test_batch_logs_db.json")
    batch_jobs_db = AioAWSBatchTinyDB(
        jobs_db_file=jobs_db_file, logs_db_file=logs_db_file
    )
    assert isinstance(batch_jobs_db, AioAWSBatchDB)
    assert batch_jobs_db.jobs_db.all() == []
    assert batch_jobs_db.logs_db.all() == []
    yield batch_jobs_db


@pytest.fixture
def redis_url(redisdb) -> str:
    with redisdb.client() as redis_client:
        yield f"unix://{redis_client.connection.path}"


@pytest.fixture
@pytest.mark.asyncio
async def aioredis_jobs_db(redis_url) -> AioAWSBatchDB:
    batch_db = AioAWSBatchRedisDB(redis_url=redis_url)
    assert isinstance(batch_db, AioAWSBatchDB)
    key_count = 0
    jobs_db = await batch_db.jobs_db_alive
    async for key in jobs_db.scan_iter():
        key_count += 1
    logs_db = await batch_db.logs_db_alive
    async for key in logs_db.scan_iter():
        key_count += 1
    assert key_count == 0
    yield batch_db


@pytest.fixture
@pytest.mark.asyncio
async def jobs_dbs(aioredis_jobs_db, aiotiny_jobs_db) -> List[AioAWSBatchDB]:
    yield [aioredis_jobs_db, aiotiny_jobs_db]


@pytest.mark.asyncio
async def test_aio_aws_batch_db_init(redis_url):
    batch_db = AioAWSBatchRedisDB(redis_url=redis_url)
    assert await batch_db.db_alive is True
    db_info = await batch_db.db_info
    assert db_info["jobs"]["redis_version"]
    assert db_info["logs"]["redis_version"]


#
# Test common ABC methods for any AioAWSBatchDB
#


@pytest.mark.asyncio
async def test_batch_job_db_save(jobs_dbs, aws_batch_job):
    job = aws_batch_job
    assert job.job_id
    assert job.job_name
    for jobs_db in jobs_dbs:
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id
        db_job = await jobs_db.find_by_job_id(job.job_id)
        assert db_job


@pytest.mark.asyncio
async def test_batch_job_db_find_by_job_id(jobs_dbs, aws_batch_job):
    job = aws_batch_job
    for jobs_db in jobs_dbs:
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id
        job_dict = await jobs_db.find_by_job_id(job.job_id)
        assert isinstance(job_dict, dict)
        assert job_dict["job_id"] == job.job_id
        assert job_dict["job_name"] == job.job_name
        assert job_dict["status"] == job.status
        # test all the fields, since it behaves like a dict
        assert job.db_data == job_dict


@pytest.mark.asyncio
async def test_batch_job_db_remove_by_job_id(jobs_dbs, aws_batch_job):
    job = aws_batch_job
    for jobs_db in jobs_dbs:
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id
        job_dict = await jobs_db.remove_by_job_id(job.job_id)
        assert isinstance(job_dict, Dict)
        assert job.db_data == job_dict


@pytest.mark.asyncio
async def test_batch_job_db_find_by_job_name(jobs_dbs, aws_batch_job):
    job = aws_batch_job
    for jobs_db in jobs_dbs:
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id
        job_dicts = await jobs_db.find_by_job_name(job.job_name)
        assert isinstance(job_dicts, List)
        assert len(job_dicts) == 1
        job_dict = job_dicts[0]
        assert isinstance(job_dict, Dict)
        assert job.db_data == job_dict


@pytest.mark.asyncio
async def test_batch_job_db_remove_by_job_name(jobs_dbs, aws_batch_job):
    job = aws_batch_job
    for jobs_db in jobs_dbs:
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id
        job_ids = await jobs_db.remove_by_job_name(job.job_name)
        assert isinstance(job_ids, Set)
        assert len(job_ids) == 1
        for job_id in job_ids:
            assert isinstance(job_id, str)
            assert job_id == job.job_id
        job_id = await jobs_db.find_by_job_id(job.job_id)
        assert job_id is None
        job_id = await jobs_db.remove_by_job_id(job.job_id)
        assert job_id is None


@pytest.mark.asyncio
async def test_batch_job_db_find_jobs_by_status(jobs_dbs, aws_batch_jobs):

    job_succeeded, job_failed, job_running = aws_batch_jobs

    for jobs_db in jobs_dbs:
        job_id = await jobs_db.save_job(job_succeeded)
        assert job_id == job_succeeded.job_id
        job_id = await jobs_db.save_job(job_failed)
        assert job_id == job_failed.job_id
        job_id = await jobs_db.save_job(job_running)
        assert job_id == job_running.job_id

        jobs = await jobs_db.find_by_job_status(job_states=["SUCCEEDED"])
        assert isinstance(jobs, List)
        assert len(jobs) == 1
        assert jobs[0].job_id == job_succeeded.job_id
        jobs = await jobs_db.find_by_job_status(job_states=["FAILED"])
        assert isinstance(jobs, List)
        assert len(jobs) == 1
        assert jobs[0].job_id == job_failed.job_id
        jobs = await jobs_db.find_by_job_status(job_states=["SUCCEEDED", "FAILED"])
        assert isinstance(jobs, List)
        assert len(jobs) == 2


@pytest.mark.asyncio
async def test_aio_batch_find_jobs_by_status_without_jobs_db(aws_batch_jobs):

    job_succeeded, job_failed, job_running = aws_batch_jobs

    # Test the AIO find functions that rely on the jobs (jobs-db optional)

    async for job in aio_find_jobs_by_status(
        jobs=aws_batch_jobs, job_states=["SUCCEEDED"]
    ):
        assert job.job_id == job_succeeded.job_id

    async for job in aio_find_jobs_by_status(
        jobs=aws_batch_jobs, job_states=["FAILED"]
    ):
        assert job.job_id == job_failed.job_id

    async for job in aio_find_complete_jobs(jobs=aws_batch_jobs):
        assert job.job_id in [job_succeeded.job_id, job_failed.job_id]
        assert job.job_id != job_running.job_id

    async for job in aio_find_running_jobs(jobs=aws_batch_jobs):
        assert job.job_id == job_running.job_id

    async for job in aio_find_running_jobs(jobs=[job_succeeded, job_failed]):
        assert job.job_id
        raise RuntimeError("Should not find any")


def test_batch_find_jobs_by_status_without_jobs_db(aws_batch_jobs):

    job_succeeded, job_failed, job_running = aws_batch_jobs

    # Test the sync find functions that rely on the jobs (jobs-db optional)

    for job in find_jobs_by_status(jobs=aws_batch_jobs, job_states=["SUCCEEDED"]):
        assert job.job_id == job_succeeded.job_id

    for job in find_jobs_by_status(jobs=aws_batch_jobs, job_states=["FAILED"]):
        assert job.job_id == job_failed.job_id

    for job in find_complete_jobs(jobs=aws_batch_jobs):
        assert job.job_id in [job_succeeded.job_id, job_failed.job_id]
        assert job.job_id != job_running.job_id

    for job in find_running_jobs(jobs=aws_batch_jobs):
        assert job.job_id == job_running.job_id

    for job in find_running_jobs(jobs=[job_succeeded, job_failed]):
        assert job.job_id
        raise RuntimeError("Should not find any")


@pytest.mark.asyncio
async def test_aio_batch_find_jobs_by_status_with_jobs_db(jobs_dbs, aws_batch_jobs):

    job_succeeded, job_failed, job_running = aws_batch_jobs

    for jobs_db in jobs_dbs:
        job_id = await jobs_db.save_job(job_succeeded)
        assert job_id == job_succeeded.job_id
        job_id = await jobs_db.save_job(job_failed)
        assert job_id == job_failed.job_id
        job_id = await jobs_db.save_job(job_running)
        assert job_id == job_running.job_id

    # Test the find functions that now check a jobs-db entry
    job_succeeded.status = None
    job_failed.status = None
    job_running.status = None

    for jobs_db in jobs_dbs:

        async for job in aio_find_jobs_by_status(
            jobs=aws_batch_jobs, job_states=["SUCCEEDED"], jobs_db=jobs_db
        ):
            assert job.job_id == job_succeeded.job_id

        async for job in aio_find_jobs_by_status(
            jobs=aws_batch_jobs, job_states=["FAILED"], jobs_db=jobs_db
        ):
            assert job.job_id == job_failed.job_id

        async for job in aio_find_complete_jobs(jobs=aws_batch_jobs, jobs_db=jobs_db):
            assert job.job_id in [job_succeeded.job_id, job_failed.job_id]
            assert job.job_id != job_running.job_id

        async for job in aio_find_running_jobs(jobs=aws_batch_jobs, jobs_db=jobs_db):
            assert job.job_id == job_running.job_id

        async for job in aio_find_running_jobs(
            jobs=[job_succeeded, job_failed], jobs_db=jobs_db
        ):
            assert job.job_id
            raise RuntimeError("Should not find any")


@pytest.mark.skip("Cannot use asyncio.run with a running event loop")
@pytest.mark.asyncio
async def test_batch_find_jobs_by_status_with_jobs_db(jobs_dbs, aws_batch_jobs):

    # Test the sync find functions that rely on the jobs-db

    # TODO: Maybe these methods should use a sync jobs-db that has the
    #       same ABC base class with sync methods?

    job_succeeded, job_failed, job_running = aws_batch_jobs

    for jobs_db in jobs_dbs:
        job_id = await jobs_db.save_job(job_succeeded)
        assert job_id == job_succeeded.job_id
        job_id = await jobs_db.save_job(job_failed)
        assert job_id == job_failed.job_id
        job_id = await jobs_db.save_job(job_running)
        assert job_id == job_running.job_id

    # Test the find functions that now check a jobs-db entry
    job_succeeded.status = None
    job_failed.status = None
    job_running.status = None

    for jobs_db in jobs_dbs:

        for job in find_jobs_by_status(
            jobs=aws_batch_jobs, job_states=["SUCCEEDED"], jobs_db=jobs_db
        ):
            assert job.job_id == job_succeeded.job_id

        for job in find_jobs_by_status(
            jobs=aws_batch_jobs, job_states=["FAILED"], jobs_db=jobs_db
        ):
            assert job.job_id == job_failed.job_id

        for job in find_complete_jobs(jobs=aws_batch_jobs, jobs_db=jobs_db):
            assert job.job_id in [job_succeeded.job_id, job_failed.job_id]
            assert job.job_id != job_running.job_id

        for job in find_running_jobs(jobs=aws_batch_jobs, jobs_db=jobs_db):
            assert job.job_id == job_running.job_id

        for job in find_running_jobs(jobs=[job_succeeded, job_failed], jobs_db=jobs_db):
            assert job.job_id
            raise RuntimeError("Should not find any")


@pytest.mark.asyncio
async def test_batch_job_db_find_jobs_to_run_empty(jobs_dbs, aws_batch_job):
    for jobs_db in jobs_dbs:
        job = AWSBatchJob(**aws_batch_job.db_data)
        assert job.job_id
        assert job.status == "SUCCEEDED"
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id
        jobs = await jobs_db.find_jobs_to_run()
        assert isinstance(jobs, List)
        assert len(jobs) == 0  # successful jobs are done


@pytest.mark.asyncio
async def test_batch_job_db_jobs_to_run_empty(jobs_dbs, aws_batch_job):
    for jobs_db in jobs_dbs:
        job = AWSBatchJob(**aws_batch_job.db_data)
        assert job.job_id
        assert job.status == "SUCCEEDED"
        jobs = await jobs_db.jobs_to_run([job])
        assert isinstance(jobs, List)
        assert len(jobs) == 0  # successful jobs are done


@pytest.mark.asyncio
async def test_batch_job_db_find_jobs_to_run(jobs_dbs, aws_batch_job):
    for jobs_db in jobs_dbs:
        job = AWSBatchJob(**aws_batch_job.db_data)
        assert job.job_id
        job.status = "SUBMITTED"  # this job can be 'recovered'
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id
        jobs = await jobs_db.find_jobs_to_run()
        assert isinstance(jobs, List)
        assert len(jobs) == 1
        assert isinstance(jobs[0], AWSBatchJob)


@pytest.mark.asyncio
async def test_batch_job_db_filter_jobs_to_run(jobs_dbs, aws_batch_job):
    for jobs_db in jobs_dbs:
        job = AWSBatchJob(**aws_batch_job.db_data)
        assert job.job_id
        job.status = "SUBMITTED"  # this job can be 'recovered'
        jobs = await jobs_db.jobs_to_run([job])
        assert isinstance(jobs, List)
        assert len(jobs) == 1
        assert isinstance(jobs[0], AWSBatchJob)


@pytest.mark.asyncio
async def test_batch_job_db_saved_filter_jobs_to_run(jobs_dbs, aws_batch_job):
    for jobs_db in jobs_dbs:
        job = AWSBatchJob(**aws_batch_job.db_data)
        assert job.job_id
        job.status = "SUBMITTED"  # this job can be 'recovered'
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id
        jobs = await jobs_db.jobs_to_run([job])
        assert isinstance(jobs, List)
        assert len(jobs) == 1
        assert isinstance(jobs[0], AWSBatchJob)


@pytest.mark.asyncio
async def test_batch_job_db_saved_filter_jobs_to_run_empty(jobs_dbs, aws_batch_job):
    for jobs_db in jobs_dbs:
        job = AWSBatchJob(**aws_batch_job.db_data)
        assert job.job_id
        assert job.status == "SUCCEEDED"
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id
        jobs = await jobs_db.jobs_to_run([job])
        assert isinstance(jobs, List)
        assert len(jobs) == 0  # successful jobs are done


@pytest.mark.asyncio
async def test_batch_job_db_saved_filter_jobs_to_run_for_recovery(
    jobs_dbs, aws_batch_job
):
    for jobs_db in jobs_dbs:
        job = AWSBatchJob(**aws_batch_job.db_data)
        assert job.job_id
        assert job.status == "SUCCEEDED"
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id
        jobs = await jobs_db.jobs_to_run([job])
        assert len(jobs) == 0  # successful jobs are done
        # Assume the job is recreated and needs to be recovered from the db
        job.reset()
        assert job.job_id is None
        assert job.job_name  # used to recover the job from the db
        jobs = await jobs_db.jobs_to_run([job])
        assert isinstance(jobs, List)
        assert len(jobs) == 0  # the job.job_name is used to recover the job


@pytest.mark.asyncio
async def test_batch_job_db_find_latest_job_name(jobs_dbs, aws_batch_job):
    for jobs_db in jobs_dbs:
        job = AWSBatchJob(**aws_batch_job.db_data)
        assert job.job_id
        assert job.status == "SUCCEEDED"
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id

        # Fake another submission of the same job-name
        new_job = AWSBatchJob(**aws_batch_job.db_data)
        new_job.job_id = job.job_id.replace("08986fbb7144", "08986fbb7145")
        new_job.job_submission["jobId"] = new_job.job_id
        new_job.job_description["status"] = "SUCCEEDED"
        new_job.status = job.job_description["status"]
        new_job.job_description["createdAt"] += 5
        new_job.job_description["startedAt"] += 5
        new_job.job_description["stoppedAt"] += 5
        job_id = await jobs_db.save_job(new_job)
        assert job_id == new_job.job_id
        job_dicts = await jobs_db.find_by_job_name(job.job_name)
        assert len(job_dicts) == 2
        assert sorted([j["job_id"] for j in job_dicts]) == sorted(
            [job.job_id, new_job.job_id]
        )
        job_found = await jobs_db.find_latest_job_name(job.job_name)
        assert job_found.job_id == new_job.job_id


@pytest.mark.asyncio
async def test_batch_job_db_saved_filter_jobs_to_run_with_duplicate(
    jobs_dbs, aws_batch_job
):
    for jobs_db in jobs_dbs:
        job = AWSBatchJob(**aws_batch_job.db_data)
        assert job.job_id

        # Fake a job failure
        job.job_description["status"] = "FAILED"
        job.status = job.job_description["status"]
        job_id = await jobs_db.save_job(job)
        assert job_id == job.job_id

        jobs = await jobs_db.jobs_to_run([job])
        assert len(jobs) == 1  # failed jobs could be run again (if reset)

        # Fake another submission of the same job-name
        new_job = AWSBatchJob(**aws_batch_job.db_data)
        new_job.job_id = job.job_id.replace("08986fbb7144", "08986fbb7145")
        new_job.job_submission["jobId"] = new_job.job_id
        new_job.job_description["status"] = "SUCCEEDED"
        new_job.status = job.job_description["status"]
        new_job.job_description["createdAt"] += 5
        new_job.job_description["startedAt"] += 5
        new_job.job_description["stoppedAt"] += 5

        # Now the latest job-db entry is SUCCEEDED
        job_id = await jobs_db.save_job(new_job)
        assert job_id == new_job.job_id

        # Note: the job-db status will override the input job FAILED status
        jobs = await jobs_db.jobs_to_run([job])
        assert len(jobs) == 0  # successful jobs are done
