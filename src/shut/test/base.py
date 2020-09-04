# -*- coding: utf8 -*-
# Copyright (c) 2020 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import abc
import enum
import datetime
import json
import os
import shutil
import subprocess as sp
import sys
from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING

from shut.model.requirements import Requirement

if TYPE_CHECKING:
  from shut.model.package import PackageModel

__all__ = [
  'TestStatus',
  'TestEnvironment',
  'StackTrace',
  'TestCrashReport',
  'TestCase',
  'TestRun',
  'Runtime',
  'Virtualenv',
  'BaseTestDriver',
]


class TestStatus(enum.Enum):
  PASSED = enum.auto()  #: The test passed.
  FAILED = enum.auto()  #: The test failed.
  ERROR = enum.auto()  #: An error occurred when running the test.


@dataclass
class TestEnvironment:
  python_version: str
  platform: Optional[str]


@dataclass
class StackTrace:
  filename: str
  lineno: int
  message: str


@dataclass
class TestCrashReport:
  filename: str
  lineno: int
  message: str
  traceback: List[StackTrace]
  longrepr: str


@dataclass
class TestCase:
  name: str
  duration: float
  filename: str
  lineno: int
  status: TestStatus
  crash: Optional[TestCrashReport]
  stdout: str


@dataclass
class TestRun:
  started: datetime.datetime
  duration: float
  status: TestStatus
  environment: TestEnvironment
  tests: List[TestCase]
  error: Optional[str] = None


@dataclass
class Runtime:
  python: List[str]
  pip: List[str] = None
  virtualenv: List[str] = None

  def __post_init__(self):
    if not self.pip:
      self.pip = self.python + ['-m', 'pip']
    if not self.virtualenv:
      self.virtualenv = self.python + ['-m', 'venv']

  @classmethod
  def current(self) -> 'Runtime':
    return Runtime([sys.executable])

  def get_environment(self) -> TestEnvironment:
    env = getattr(self, '_environment', None)
    if env is None:
      code = 'import sys, platform, json\n'\
            'print(json.dumps({"version": sys.version, "platform": platform.platform()}))'
      raw = json.loads(sp.check_output(self.python + ['-c', code]).decode())
      env =TestEnvironment(raw['version'], raw['platform'])
      self._environment = env
    return env


@dataclass
class Virtualenv:
  path: str

  def exists(self) -> bool:
    return os.path.isdir(self.path)

  def create(self, runtime: Runtime) -> None:
    """
    Create the virtual environment.
    """

    sp.check_call(runtime.virtualenv + [self.path])

  def rm(self):
    if os.path.isdir(self.path):
      shutil.rmtree(self.path)

  def bin(self, name):
    if os.name == 'nt':
      name += '.exe'
    return os.path.join(self.path, 'Scripts' if os.name == 'nt' else 'bin', name)

  def get_runtime(self) -> Runtime:
    return Runtime([self.bin('python')])


class BaseTestDriver(metaclass=abc.ABCMeta):
  """
  Base class for drivers that can run unit tests for a package.
  """

  @abc.abstractmethod
  def test_package(self, package: 'PackageModel', runtime: Runtime) -> TestRun:
    pass

  @abc.abstractmethod
  def get_test_requirements(self) -> List[Requirement]:
    pass
