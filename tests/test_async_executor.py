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

"""
Test the aio_aws.async_executor module
"""
import asyncio
from types import ModuleType

from aio_aws import async_executor


def test_async_executor_module():
    assert isinstance(async_executor, ModuleType)


def test_async_executor_alive():
    executor = async_executor.AsyncioExecutor()
    assert executor.is_alive()

    # clean up
    executor.shutdown()
    assert not executor.is_alive()


def test_async_executor_shutdown():
    # https://docs.python.org/3/library/asyncio-eventloop.html#running-and-stopping-the-loop
    executor = async_executor.AsyncioExecutor()
    assert executor.is_alive()
    executor.shutdown()  # waits on any running tasks
    assert not executor.is_alive()
    assert not executor.loop.is_running()
    # But do not close the loop, it's irreversible; allow restarts
    assert not executor.loop.is_closed()


def test_async_executor_start_idempotent():
    executor = async_executor.AsyncioExecutor()
    assert executor.is_alive()
    loop_before = executor.loop
    assert executor.start()  # should be running already, do nothing
    loop_after = executor.loop
    assert id(loop_before) == id(loop_after)

    executor.shutdown()
    assert not executor.is_alive()
    # But do not close the loop, it's irreversible; allow restarts
    assert not executor.loop.is_closed()

    # restart the loop
    assert executor.start()
    assert executor.is_alive()
    loop_after = executor.loop
    assert id(loop_before) == id(loop_after)


def test_async_executor_restart():
    executor = async_executor.AsyncioExecutor()
    assert executor.is_alive()
    loop_before = executor.loop

    executor.shutdown()
    assert not executor.is_alive()
    assert not executor.loop.is_running()
    # But do not close the loop, it's irreversible; allow restarts
    assert not executor.loop.is_closed()

    # restart it
    assert executor.start()  # should start it again
    assert executor.is_alive()
    assert executor.loop.is_running()
    loop_after = executor.loop
    assert id(loop_before) == id(loop_after)


def test_async_executor_loop_ownership():
    # test that executors own a new event loop and run it
    # in their own thread; not sure what the limits are to
    # how many executor-loops can be spawned, but the class
    # does not use any kind of thread pool (yet).
    executor1 = async_executor.AsyncioExecutor()
    assert executor1.is_alive()
    executor2 = async_executor.AsyncioExecutor()
    assert executor2.is_alive()
    assert executor1.loop is not executor2.loop

    executor1.shutdown()
    assert not executor1.is_alive()
    assert executor2.is_alive()  # no impact on executor2
    assert executor2.loop.is_running()
    executor2.shutdown()
    assert not executor2.is_alive()


def test_async_executor_submit_coroutine_function(monkeypatch):
    monkeypatch.setattr(async_executor, "MIN_PAUSE", 0.0)
    monkeypatch.setattr(async_executor, "MAX_PAUSE", 0.5)

    executor = async_executor.AsyncioExecutor()
    task = executor.submit(async_executor.delay, 1)
    executor.shutdown()  # waits on running tasks
    assert task.done()
    pause = task.result()
    assert isinstance(pause, float)
    assert async_executor.MIN_PAUSE == 0.0
    assert async_executor.MAX_PAUSE == 0.5
    assert async_executor.MIN_PAUSE <= pause <= async_executor.MAX_PAUSE


def test_async_executor_submit_coroutine_object(monkeypatch):
    monkeypatch.setattr(async_executor, "MIN_PAUSE", 0.0)
    monkeypatch.setattr(async_executor, "MAX_PAUSE", 0.5)

    executor = async_executor.AsyncioExecutor()
    delay_coro = async_executor.delay(1)
    delay_task = executor.submit(delay_coro)
    executor.shutdown()  # waits on running tasks
    assert delay_task.done()
    pause = delay_task.result()
    assert isinstance(pause, float)
    assert async_executor.MIN_PAUSE == 0.0
    assert async_executor.MAX_PAUSE == 0.5
    assert async_executor.MIN_PAUSE <= pause <= async_executor.MAX_PAUSE


def test_async_executor_submit_generator_function():
    executor = async_executor.AsyncioExecutor()

    generator_task = executor.submit(asyncio.sleep, 0.01)
    executor.shutdown()  # waits on running tasks
    assert not executor.is_alive()
    assert generator_task.done()
    assert generator_task.result() is None


def test_async_executor_submit_generator_object():
    executor = async_executor.AsyncioExecutor()

    generator_obj = asyncio.sleep(0.01)
    generator_task = executor.submit(generator_obj)
    executor.shutdown()  # waits on running tasks
    assert not executor.is_alive()
    assert generator_task.done()
    assert generator_task.result() is None
