# Lint as: python3
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=unused-variable

from absl import logging
from absl.testing import absltest
import numpy as np
from pyiree import compiler2 as compiler
from pyiree import rt


def create_add_scalar_module():
  binary = compiler.compile_str("""
    func @add_scalar(%arg0: i32, %arg1: i32) -> i32 attributes { iree.module.export } {
      %0 = addi %arg0, %arg1 : i32
      return %0 : i32
    }
    """,
                                target_backends=["vmla"])
  m = rt.VmModule.from_flatbuffer(binary)
  return m


def create_simple_static_mul_module():
  binary = compiler.compile_str("""
    func @simple_mul(%arg0: tensor<4xf32>, %arg1: tensor<4xf32>) -> tensor<4xf32>
          attributes { iree.module.export } {
        %0 = "mhlo.multiply"(%arg0, %arg1) {name = "mul.1"} : (tensor<4xf32>, tensor<4xf32>) -> tensor<4xf32>
        return %0 : tensor<4xf32>
    }
    """,
                                target_backends=["vmla"])
  m = rt.VmModule.from_flatbuffer(binary)
  return m


def create_simple_dynamic_abs_module():
  # TODO(laurenzo): Compile for more backends as dynamic shapes come online.
  target_backends = ["vmla"]
  binary = compiler.compile_str("""
    func @simple_mul(%arg0: tensor<?x?xf32>) -> tensor<?x?xf32>
          attributes { iree.module.export } {
        %0 = "mhlo.abs"(%arg0) : (tensor<?x?xf32>) -> tensor<?x?xf32>
        return %0 : tensor<?x?xf32>
    }
    """,
                                target_backends=target_backends)
  m = rt.VmModule.from_flatbuffer(binary)
  return m


class VmTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    driver_names = rt.HalDriver.query()
    logging.info("driver_names: %s", driver_names)
    cls.driver = rt.HalDriver.create("vmla")
    cls.device = cls.driver.create_default_device()
    cls.hal_module = rt.create_hal_module(cls.device)
    cls.htf = rt.HostTypeFactory.get_numpy()

  def test_variant_list(self):
    l = rt.VmVariantList(5)
    logging.info("variant_list: %s", l)
    self.assertEqual(l.size, 0)

  def test_context_id(self):
    instance = rt.VmInstance()
    context1 = rt.VmContext(instance)
    context2 = rt.VmContext(instance)
    self.assertGreater(context2.context_id, context1.context_id)

  def test_module_basics(self):
    m = create_simple_static_mul_module()
    f = m.lookup_function("simple_mul")
    self.assertGreater(f.ordinal, 0)
    notfound = m.lookup_function("notfound")
    self.assertIs(notfound, None)

  def test_dynamic_module_context(self):
    instance = rt.VmInstance()
    context = rt.VmContext(instance)
    m = create_simple_static_mul_module()
    context.register_modules([self.hal_module, m])

  def test_static_module_context(self):
    m = create_simple_static_mul_module()
    logging.info("module: %s", m)
    instance = rt.VmInstance()
    logging.info("instance: %s", instance)
    context = rt.VmContext(instance, modules=[self.hal_module, m])
    logging.info("context: %s", context)

  def test_dynamic_shape_compile(self):
    m = create_simple_dynamic_abs_module()
    logging.info("module: %s", m)
    instance = rt.VmInstance()
    logging.info("instance: %s", instance)
    context = rt.VmContext(instance, modules=[self.hal_module, m])
    logging.info("context: %s", context)

  def test_add_scalar(self):
    m = create_add_scalar_module()
    instance = rt.VmInstance()
    context = rt.VmContext(instance, modules=[self.hal_module, m])
    f = m.lookup_function("add_scalar")
    abi = context.create_function_abi(self.device, self.htf, f)
    logging.info("abi: %s", abi)

    inputs = abi.pack_inputs(5, 6)
    logging.info("serialize_inputs: %s", abi.serialize_vm_list(inputs))
    logging.info("inputs: %s", inputs)

    allocated_results = abi.allocate_results(inputs, static_alloc=False)
    logging.info("allocated_results: %s", allocated_results)
    logging.info("Invoking...")
    context.invoke(f, inputs, allocated_results)
    logging.info("...done")

    result = abi.unpack_results(allocated_results)
    logging.info("result: %s", result)
    self.assertEqual(result, 11)

  def test_synchronous_dynamic_shape_invoke_function(self):
    m = create_simple_dynamic_abs_module()
    instance = rt.VmInstance()
    context = rt.VmContext(instance, modules=[self.hal_module, m])
    f = m.lookup_function("simple_mul")
    abi = context.create_function_abi(self.device, self.htf, f)
    logging.info("abi: %s", abi)

    arg0 = np.array([[-1., 2.], [3., -4.]], dtype=np.float32)
    inputs = abi.pack_inputs(arg0)
    logging.info("Serialized inputs: %s", abi.serialize_vm_list(inputs))
    logging.info("inputs: %s", inputs)

    allocated_results = abi.allocate_results(inputs, static_alloc=False)
    logging.info("allocated_results: %s", allocated_results)
    logging.info("Invoking...")
    context.invoke(f, inputs, allocated_results)
    logging.info("...done")

    result = abi.unpack_results(allocated_results)
    logging.info("result: %s", result)
    np.testing.assert_allclose(result, [[1., 2.], [3., 4.]])

  def test_synchronous_invoke_function(self):
    m = create_simple_static_mul_module()
    instance = rt.VmInstance()
    context = rt.VmContext(instance, modules=[self.hal_module, m])
    f = m.lookup_function("simple_mul")
    abi = context.create_function_abi(self.device, self.htf, f)
    logging.info("abi: %s", abi)

    arg0 = np.array([1., 2., 3., 4.], dtype=np.float32)
    arg1 = np.array([4., 5., 6., 7.], dtype=np.float32)
    inputs = abi.pack_inputs(arg0, arg1)
    logging.info("Serialized inputs: %s", abi.serialize_vm_list(inputs))
    logging.info("inputs: %s", inputs)

    allocated_results = abi.allocate_results(inputs, static_alloc=False)
    logging.info("allocated_results: %s", allocated_results)
    logging.info("Invoking...")
    context.invoke(f, inputs, allocated_results)
    logging.info("...done")

    result = abi.unpack_results(allocated_results)
    logging.info("result: %s", result)
    np.testing.assert_allclose(result, [4., 10., 18., 28.])


if __name__ == "__main__":
  absltest.main()
