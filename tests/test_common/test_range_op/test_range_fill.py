# Copyright (c) 2025 SandAI. All Rights Reserved.
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

import unittest
from unittest import TestCase

import torch

from magi_attention.common.range_op import range_fill_


def range_fill_ref(
    out: torch.Tensor,
    ranges: torch.Tensor,
    val: float,
    dim: int = 0,
) -> torch.Tensor:
    # Return directly if ranges or tensor is empty
    if ranges.shape[0] == 0 or out.numel() == 0:
        return out

    # Handle the case when dim is not 0
    if dim != 0:
        out = out.transpose(0, dim).contiguous()
    else:
        out = out.contiguous()

    # Iterate through each range and fill with the specified value
    for start, end in ranges:
        out[start:end].fill_(val)

    # If transposed earlier, transpose back
    if dim != 0:
        out = out.transpose(0, dim)

    return out


class TestRangeFill(TestCase):
    def test_range_fill(self):
        """Test range_fill_ function by comparing with reference implementation"""

        # Helper function to compare implementations
        def compare_implementations(
            input_tensor, ranges, cu_range_sizes, total_size, val, dim=0
        ):
            # Copy input tensors for comparison
            input_copy1 = input_tensor.clone()
            input_copy2 = input_tensor.clone()

            # Call the original implementation
            result = range_fill_(
                input=input_copy1,
                ranges=ranges,
                cu_range_sizes=cu_range_sizes,
                total_size=total_size,
                val=val,
                dim=dim,
            )

            # Call the reference implementation
            expected = range_fill_ref(
                out=input_copy2,
                ranges=ranges,
                val=val,
                dim=dim,
            )

            # Verify results match
            assert torch.equal(result, expected)
            return result, expected

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Test case 1: Basic functionality
        input_tensor = torch.zeros(10, 5, device=device)
        ranges = torch.tensor([[0, 3], [5, 8]], dtype=torch.int32, device=device)
        cu_range_sizes = torch.tensor([0, 3], dtype=torch.int32, device=device)
        total_size = 6
        val = 1.0

        compare_implementations(input_tensor, ranges, cu_range_sizes, total_size, val)

        # Test case 2: Empty tensor handling
        empty_input = torch.empty(0, 5, device=device)
        empty_ranges = torch.empty(0, 2, dtype=torch.int32, device=device)
        empty_cu_sizes = torch.empty(0, dtype=torch.int32, device=device)

        compare_implementations(empty_input, empty_ranges, empty_cu_sizes, 0, val, 0)

        # Test case 3: Different dimension (dim=1)
        input_tensor = torch.zeros(5, 10, 3, device=device)
        ranges = torch.tensor([[0, 3], [5, 8]], dtype=torch.int32, device=device)
        cu_range_sizes = torch.tensor([0, 3], dtype=torch.int32, device=device)
        total_size = 6

        compare_implementations(
            input_tensor, ranges, cu_range_sizes, total_size, val, dim=1
        )

        # Test case 4: Large tensors
        large_input = torch.zeros(100, 20, device=device)
        large_ranges = torch.tensor(
            [[0, 30], [40, 80]], dtype=torch.int32, device=device
        )
        large_cu_sizes = torch.tensor([0, 30], dtype=torch.int32, device=device)
        large_total_size = 70

        compare_implementations(
            large_input, large_ranges, large_cu_sizes, large_total_size, val
        )

        # Test case 5: Edge case - single range
        single_range_input = torch.zeros(10, 5, device=device)
        single_range = torch.tensor([[3, 7]], dtype=torch.int32, device=device)
        single_cu_size = torch.tensor([0], dtype=torch.int32, device=device)

        compare_implementations(
            single_range_input, single_range, single_cu_size, 4, val
        )

        # Test case 6: Multi-dimensional tensors
        multi_dim_input = torch.zeros(10, 5, 8, 4, device=device)

        compare_implementations(
            multi_dim_input, ranges, cu_range_sizes, total_size, val, dim=0
        )
        compare_implementations(
            multi_dim_input, ranges, cu_range_sizes, total_size, val, dim=2
        )

        # Test case 7: Non-contiguous memory layout
        non_contiguous_input = torch.zeros(10, 5, device=device).transpose(0, 1)
        assert not non_contiguous_input.is_contiguous()

        compare_implementations(
            non_contiguous_input,
            ranges,
            cu_range_sizes,
            total_size,
            val,
            dim=1,
        )

        # Test case 8: Various data types
        for dtype in [torch.float16, torch.float32, torch.int32, torch.int64]:
            typed_input = torch.zeros(10, 5, device=device).to(dtype)
            if dtype.is_floating_point:
                compare_implementations(
                    typed_input, ranges, cu_range_sizes, total_size, val
                )

        # Test case 9: Random data large-scale testing
        for _ in range(5):
            # Randomly generate inputs
            input_size = torch.randint(20, 50, (1,)).item()
            feature_size = torch.randint(5, 15, (1,)).item()
            input_tensor = torch.zeros(input_size, feature_size, device=device)

            # Randomly generate ranges
            num_ranges = torch.randint(1, 10, (1,)).item()
            ranges_list = []
            sizes_list = [0]

            for _ in range(num_ranges):
                start = torch.randint(0, input_size - 5, (1,)).item()
                end = torch.randint(
                    start + 1, min(start + 10, input_size) + 1, (1,)
                ).item()
                ranges_list.append([start, end])
                sizes_list.append(sizes_list[-1] + (end - start))

            ranges = torch.tensor(ranges_list, dtype=torch.int32, device=device)
            cu_range_sizes = torch.tensor(
                sizes_list[:-1], dtype=torch.int32, device=device
            )
            total_size = sizes_list[-1]

            # Test different fill values
            for val in [0.0, 1.0, -1.0, 3.14, 42.0]:
                compare_implementations(
                    input_tensor.clone(), ranges, cu_range_sizes, total_size, val
                )


if __name__ == "__main__":
    unittest.main()
