# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools
import threading

_lock = threading.Lock()
MAX_LABELS_COUNT = 64


def class_logger(api_methods=None):
    """Decorator that adds logging functionality to each method of the class."""

    def decorator(decorated_cls):
        for attr_name, attr_value in decorated_cls.__dict__.items():

            if callable(attr_value):
                setattr(
                    decorated_cls, attr_name, method_logger(attr_value, decorated_cls)
                )

        # Initialize or extend _api_methods attribute
        decorated_cls._api_methods = getattr(decorated_cls, "_api_methods", [])
        if api_methods:
            decorated_cls._api_methods.extend(api_methods)

        return decorated_cls

    return decorator


def method_logger(method, cls):
    """Decorator that adds logging functionality to a method."""

    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        api_method_name = str(method.__name__)
        # Track regular and "dunder" methods
        if api_method_name.startswith("__") or not api_method_name.startswith("_"):
            add_api_method(api_method_name, cls)
        try:
            result = method(*args, **kwargs)
            return result
        except Exception as e:
            raise e

    return wrapper


def add_api_method(api_method_name, cls):
    global _lock
    with _lock:
        # Push the method to the front of the _api_methods list
        cls._api_methods.insert(0, api_method_name)
        # Keep the list length within the maximum limit (adjust MAX_LABELS_COUNT as needed)
        cls._api_methods = cls._api_methods[:MAX_LABELS_COUNT]


def get_and_reset_api_methods(cls):
    global _lock
    with _lock:
        previous_api_methods = list(cls._api_methods)
        cls._api_methods.clear()
    return previous_api_methods
