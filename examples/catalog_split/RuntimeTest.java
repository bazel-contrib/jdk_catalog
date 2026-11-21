// Copyright 2026 The Bazel Authors. All rights reserved.
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import java.io.DataInputStream;

/** Checks the actual runtime patch version and the compiler's class-file version. */
public class RuntimeTest {
  public static void main(String[] args) throws Exception {
    if (args.length != 1) {
      throw new IllegalArgumentException("Pass the expected java.version as --test_arg");
    }
    String actual = System.getProperty("java.version");
    if (!actual.equals(args[0])) {
      throw new AssertionError("Expected " + args[0] + ", got " + actual);
    }
    try (var in = new DataInputStream(RuntimeTest.class.getResourceAsStream("RuntimeTest.class"))) {
      if (in.readInt() != 0xCAFEBABE) {
        throw new AssertionError("Invalid class file");
      }
      in.readUnsignedShort();
      int classVersion = in.readUnsignedShort();
      if (classVersion != Runtime.version().feature() + 44) {
        throw new AssertionError("Unexpected compiler class version " + classVersion);
      }
    }
    System.out.println("Verified java.version=" + actual + "; runtime=" + Runtime.version());
  }
}
