// Copyright 2021 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef IREE_COMPILER_DIALECT_VM_TARGET_CALLINGCONVENTIONUTILS_H_
#define IREE_COMPILER_DIALECT_VM_TARGET_CALLINGCONVENTIONUTILS_H_

#include "iree/compiler/Dialect/VM/IR/VMOps.h"

namespace mlir {
namespace iree_compiler {
namespace IREE {
namespace VM {

// Generates a string encoding the function type for defining the
// FunctionSignatureDef::calling_convention field for import functions.
//
// This differs from makeCallingConventionString in that it supports variadic
// arguments. Ideally we'd combine the two, but we only have this additional
// metadata on IREE::VM::ImportOp.
Optional<std::string> makeImportCallingConventionString(
    IREE::VM::ImportOp importOp);

// Generates a string encoding the function type for defining the
// FunctionSignatureDef::calling_convention field for internal/export functions.
Optional<std::string> makeCallingConventionString(IREE::VM::FuncOp funcOp);

}  // namespace VM
}  // namespace IREE
}  // namespace iree_compiler
}  // namespace mlir

#endif  // IREE_COMPILER_DIALECT_VM_TARGET_CALLINGCONVENTIONUTILS_H_
