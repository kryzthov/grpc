# Copyright 2015, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import abc
import collections

# assembly_interfaces is referenced from specification in this module.
from grpc.framework.assembly import interfaces as assembly_interfaces  # pylint: disable=unused-import
from grpc.framework.assembly import utilities as assembly_utilities
from grpc.early_adopter import _reexport
from grpc.early_adopter import interfaces


# TODO(issue 726): Kill the "implementations" attribute of this in favor
# of the same-information-less-bogusly-represented "cardinalities".
class InvocationBreakdown(object):
  """An intermediate representation of invocation-side views of RPC methods.

  Attributes:
    cardinalities: A dictionary from RPC method name to interfaces.Cardinality
      value.
    implementations: A dictionary from RPC method name to
      assembly_interfaces.MethodImplementation describing the method.
    request_serializers: A dictionary from RPC method name to callable
      behavior to be used serializing request values for the RPC.
    response_deserializers: A dictionary from RPC method name to callable
      behavior to be used deserializing response values for the RPC.
  """
  __metaclass__ = abc.ABCMeta


class _EasyInvocationBreakdown(
    InvocationBreakdown,
    collections.namedtuple(
        '_EasyInvocationBreakdown',
        ('cardinalities', 'implementations', 'request_serializers',
         'response_deserializers'))):
  pass


class ServiceBreakdown(object):
  """An intermediate representation of service-side views of RPC methods.

  Attributes:
    implementations: A dictionary from RPC method name
      assembly_interfaces.MethodImplementation implementing the RPC method.
    request_deserializers: A dictionary from RPC method name to callable
      behavior to be used deserializing request values for the RPC.
    response_serializers: A dictionary from RPC method name to callable
      behavior to be used serializing response values for the RPC.
  """
  __metaclass__ = abc.ABCMeta


class _EasyServiceBreakdown(
    ServiceBreakdown,
    collections.namedtuple(
        '_EasyServiceBreakdown',
        ('implementations', 'request_deserializers', 'response_serializers'))):
  pass


def break_down_invocation(method_descriptions):
  """Derives an InvocationBreakdown from several RPC method descriptions.

  Args:
    method_descriptions: A dictionary from RPC method name to
      interfaces.RpcMethodInvocationDescription describing the RPCs.

  Returns:
    An InvocationBreakdown corresponding to the given method descriptions.
  """
  cardinalities = {}
  implementations = {}
  request_serializers = {}
  response_deserializers = {}
  for name, method_description in six.iteritems(method_descriptions):
    cardinality = method_description.cardinality()
    cardinalities[name] = cardinality
    if cardinality is interfaces.Cardinality.UNARY_UNARY:
      implementations[name] = assembly_utilities.unary_unary_inline(None)
    elif cardinality is interfaces.Cardinality.UNARY_STREAM:
      implementations[name] = assembly_utilities.unary_stream_inline(None)
    elif cardinality is interfaces.Cardinality.STREAM_UNARY:
      implementations[name] = assembly_utilities.stream_unary_inline(None)
    elif cardinality is interfaces.Cardinality.STREAM_STREAM:
      implementations[name] = assembly_utilities.stream_stream_inline(None)
    request_serializers[name] = method_description.serialize_request
    response_deserializers[name] = method_description.deserialize_response
  return _EasyInvocationBreakdown(
      cardinalities, implementations, request_serializers,
      response_deserializers)


def break_down_service(method_descriptions):
  """Derives a ServiceBreakdown from several RPC method descriptions.

  Args:
    method_descriptions: A dictionary from RPC method name to
      interfaces.RpcMethodServiceDescription describing the RPCs.

  Returns:
    A ServiceBreakdown corresponding to the given method descriptions.
  """
  implementations = {}
  request_deserializers = {}
  response_serializers = {}
  for name, method_description in six.iteritems(method_descriptions):
    cardinality = method_description.cardinality()
    if cardinality is interfaces.Cardinality.UNARY_UNARY:
      def service(
          request, face_rpc_context,
          service_behavior=method_description.service_unary_unary):
        return service_behavior(
            request, _reexport.rpc_context(face_rpc_context))
      implementations[name] = assembly_utilities.unary_unary_inline(service)
    elif cardinality is interfaces.Cardinality.UNARY_STREAM:
      def service(
          request, face_rpc_context,
          service_behavior=method_description.service_unary_stream):
        return service_behavior(
            request, _reexport.rpc_context(face_rpc_context))
      implementations[name] = assembly_utilities.unary_stream_inline(service)
    elif cardinality is interfaces.Cardinality.STREAM_UNARY:
      def service(
          request_iterator, face_rpc_context,
          service_behavior=method_description.service_stream_unary):
        return service_behavior(
            request_iterator, _reexport.rpc_context(face_rpc_context))
      implementations[name] = assembly_utilities.stream_unary_inline(service)
    elif cardinality is interfaces.Cardinality.STREAM_STREAM:
      def service(
          request_iterator, face_rpc_context,
          service_behavior=method_description.service_stream_stream):
        return service_behavior(
            request_iterator, _reexport.rpc_context(face_rpc_context))
      implementations[name] = assembly_utilities.stream_stream_inline(service)
    request_deserializers[name] = method_description.deserialize_request
    response_serializers[name] = method_description.serialize_response

  return _EasyServiceBreakdown(
      implementations, request_deserializers, response_serializers)
