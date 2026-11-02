// Copyright 2026 The Bazel Authors. All rights reserved.
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package hello;

import java.io.DataInputStream;
import java.io.IOException;

/** Verifies that the consuming module selects Java 27 compilation and execution. */
public class ToolchainTest {
  public static void main(String[] args) throws IOException {
    if (Runtime.version().feature() != 27) {
      throw new AssertionError("Expected JDK 27 runtime, got " + Runtime.version());
    }
    try (var in =
        new DataInputStream(ToolchainTest.class.getResourceAsStream("ToolchainTest.class"))) {
      if (in.readInt() != 0xCAFEBABE) {
        throw new AssertionError("Invalid class file");
      }
      in.readUnsignedShort(); // Minor version.
      int major = in.readUnsignedShort();
      if (major != 71) { // Java 27 class file version.
        throw new AssertionError("Expected Java 27 bytecode (71), got " + major);
      }
    }
  }
}
