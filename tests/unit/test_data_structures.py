"""
Unit tests for core data structures.

Tests the Vector2, VectorArray, and other fundamental data structures
used throughout the game engine.
"""
import pytest
import numpy as np

from src.core.data_structures import Vector2, VectorArray


class TestVector2:
    """Test the Vector2 class."""
    
    def test_initialization(self):
        """Test Vector2 initialization."""
        v = Vector2(3, 4)  # Vector2(y, x)
        assert v.y == 3
        assert v.x == 4
    
    def test_equality(self):
        """Test Vector2 equality comparison."""
        v1 = Vector2(3, 4)
        v2 = Vector2(3, 4)
        v3 = Vector2(4, 3)
        
        assert v1 == v2
        assert v1 != v3
        assert not (v1 == v3)
    
    def test_inequality(self):
        """Test Vector2 inequality comparison."""
        v1 = Vector2(3, 4)
        v2 = Vector2(4, 3)
        
        assert v1 != v2
        assert not (v1 != Vector2(3, 4))
    
    def test_hash(self):
        """Test Vector2 hashing for use in sets and dicts."""
        v1 = Vector2(3, 4)
        v2 = Vector2(3, 4)
        v3 = Vector2(4, 3)
        
        # Equal vectors should have same hash
        assert hash(v1) == hash(v2)
        
        # Different vectors should have different hashes (usually)
        assert hash(v1) != hash(v3)
        
        # Can be used in sets and dicts
        vector_set = {v1, v2, v3}
        assert len(vector_set) == 2  # v1 and v2 are the same
    
    def test_string_representation(self):
        """Test Vector2 string representation."""
        v = Vector2(3, 4)
        repr_str = repr(v)
        assert "Vector2" in repr_str
        assert "3" in repr_str
        assert "4" in repr_str
    
    def test_addition(self):
        """Test Vector2 addition."""
        v1 = Vector2(3, 4)
        v2 = Vector2(1, 2)
        result = v1 + v2
        
        assert result.y == 4  # 3 + 1
        assert result.x == 6  # 4 + 2
        assert isinstance(result, Vector2)
    
    def test_subtraction(self):
        """Test Vector2 subtraction."""
        v1 = Vector2(5, 7)
        v2 = Vector2(2, 3)
        result = v1 - v2
        
        assert result.y == 3  # 5 - 2
        assert result.x == 4  # 7 - 3
        assert isinstance(result, Vector2)
    
    def test_multiplication(self):
        """Test Vector2 scalar multiplication."""
        v = Vector2(3, 4)
        result = v * 2
        
        assert result.y == 6  # 3 * 2
        assert result.x == 8  # 4 * 2
        assert isinstance(result, Vector2)
    
    def test_floor_division(self):
        """Test Vector2 floor division."""
        v = Vector2(7, 9)
        result = v // 2
        
        assert result.y == 3  # 7 // 2
        assert result.x == 4  # 9 // 2
        assert isinstance(result, Vector2)
    
    def test_iteration(self):
        """Test Vector2 iteration (y, x order)."""
        v = Vector2(3, 4)
        coords = list(v)
        
        assert coords == [3, 4]  # y, x order
        
        # Test unpacking
        y, x = v
        assert y == 3
        assert x == 4
    
    def test_indexing(self):
        """Test Vector2 indexed access."""
        v = Vector2(3, 4)
        
        assert v[0] == 3  # y coordinate
        assert v[1] == 4  # x coordinate
        
        with pytest.raises(IndexError):
            _ = v[2]
        
        with pytest.raises(IndexError):
            _ = v[-3]
    
    def test_distance_to(self):
        """Test Euclidean distance calculation."""
        v1 = Vector2(0, 0)
        v2 = Vector2(3, 4)
        
        distance = v1.distance_to(v2)
        assert abs(distance - 5.0) < 0.001  # 3-4-5 triangle
        
        # Test symmetric property
        assert abs(v1.distance_to(v2) - v2.distance_to(v1)) < 0.001
    
    def test_manhattan_distance_to(self):
        """Test Manhattan distance calculation."""
        v1 = Vector2(1, 1)
        v2 = Vector2(4, 5)
        
        distance = v1.manhattan_distance_to(v2)
        assert distance == 7  # |4-1| + |5-1| = 3 + 4 = 7
        
        # Test symmetric property
        assert v1.manhattan_distance_to(v2) == v2.manhattan_distance_to(v1)
    
    def test_magnitude(self):
        """Test vector magnitude calculation."""
        v1 = Vector2(0, 0)
        assert v1.magnitude() == 0.0
        
        v2 = Vector2(3, 4)
        assert abs(v2.magnitude() - 5.0) < 0.001  # 3-4-5 triangle
    
    def test_normalize(self):
        """Test vector normalization."""
        # Zero vector
        v1 = Vector2(0, 0)
        normalized = v1.normalize()
        assert normalized == Vector2(0, 0)
        
        # Non-zero vector
        v2 = Vector2(3, 4)
        normalized = v2.normalize()
        # Due to integer conversion, this won't be exactly unit length
        assert isinstance(normalized, Vector2)
    
    def test_from_tuple(self):
        """Test Vector2 creation from tuple."""
        coords = (3, 4)
        v = Vector2.from_tuple(coords)
        
        assert v.y == 3
        assert v.x == 4
    
    def test_from_list(self):
        """Test Vector2 creation from list."""
        coords = [3, 4, 5]  # Extra elements should be ignored
        v = Vector2.from_list(coords)
        
        assert v.y == 3
        assert v.x == 4
        
        with pytest.raises(ValueError):
            Vector2.from_list([3])  # Too few elements
    
    def test_to_tuple(self):
        """Test Vector2 conversion to tuple."""
        v = Vector2(3, 4)
        coords = v.to_tuple()
        
        assert coords == (3, 4)  # y, x order
        assert isinstance(coords, tuple)
    
    def test_numpy_conversion(self):
        """Test Vector2 numpy array conversion."""
        v = Vector2(3, 4)
        arr = v.to_numpy()
        
        assert arr.shape == (2,)
        assert arr[0] == 3  # y
        assert arr[1] == 4  # x
        assert arr.dtype == np.int16
        
        # Test round trip
        v2 = Vector2.from_numpy(arr)
        assert v2 == v
        
        # Test invalid array shape
        with pytest.raises(ValueError):
            Vector2.from_numpy(np.array([1, 2, 3]))
    
    @pytest.mark.parametrize("y,x", [
        (0, 0),
        (100, 200),
        (-50, 75),
        (1, -1),
    ])
    def test_various_coordinates(self, y: int, x: int):
        """Test Vector2 with various coordinate values."""
        v = Vector2(y, x)
        assert v.y == y
        assert v.x == x
        
        # Test round trip through tuple
        coords = v.to_tuple()
        v2 = Vector2.from_tuple(coords)
        assert v == v2


class TestVectorArray:
    """Test the VectorArray class."""
    
    def test_initialization_empty(self):
        """Test VectorArray initialization with no arguments."""
        arr = VectorArray()
        assert len(arr) == 0
        assert arr.data.shape == (0, 2)
    
    def test_initialization_with_vectors(self):
        """Test VectorArray initialization with Vector2 list."""
        vectors = [Vector2(1, 2), Vector2(3, 4), Vector2(5, 6)]
        arr = VectorArray(vectors)
        
        assert len(arr) == 3
        assert arr.data.shape == (3, 2)
        
        # Check data content (y, x ordering)
        assert arr.data[0, 0] == 1  # y of first vector
        assert arr.data[0, 1] == 2  # x of first vector
        assert arr.data[1, 0] == 3  # y of second vector
        assert arr.data[1, 1] == 4  # x of second vector
    
    def test_initialization_with_numpy(self):
        """Test VectorArray initialization with numpy array."""
        data = np.array([[1, 2], [3, 4]], dtype=np.int16)
        arr = VectorArray(data)
        
        assert len(arr) == 2
        assert arr.data.shape == (2, 2)
        assert np.array_equal(arr.data, data)
        
        # Test invalid shape
        with pytest.raises(ValueError):
            VectorArray(np.array([1, 2, 3]))
    
    def test_coordinate_properties(self):
        """Test y_coords and x_coords properties."""
        vectors = [Vector2(1, 2), Vector2(3, 4)]
        arr = VectorArray(vectors)
        
        assert np.array_equal(arr.y_coords, [1, 3])
        assert np.array_equal(arr.x_coords, [2, 4])
    
    def test_indexing(self):
        """Test VectorArray indexing."""
        vectors = [Vector2(1, 2), Vector2(3, 4)]
        arr = VectorArray(vectors)
        
        assert arr[0] == Vector2(1, 2)
        assert arr[1] == Vector2(3, 4)
        assert arr[-1] == Vector2(3, 4)
        
        with pytest.raises(IndexError):
            _ = arr[2]
    
    def test_iteration(self):
        """Test VectorArray iteration."""
        vectors = [Vector2(1, 2), Vector2(3, 4)]
        arr = VectorArray(vectors)
        
        result = list(arr)
        assert result == vectors
    
    def test_to_vector_list(self):
        """Test conversion back to Vector2 list."""
        vectors = [Vector2(1, 2), Vector2(3, 4)]
        arr = VectorArray(vectors)
        
        result = arr.to_vector_list()
        assert result == vectors
        assert all(isinstance(v, Vector2) for v in result)
    
    def test_distance_to_point(self):
        """Test Euclidean distance calculation to a point."""
        vectors = [Vector2(0, 0), Vector2(3, 4)]
        arr = VectorArray(vectors)
        target = Vector2(0, 0)
        
        distances = arr.distance_to_point(target)
        assert distances.shape == (2,)
        assert abs(distances[0] - 0.0) < 0.001
        assert abs(distances[1] - 5.0) < 0.001  # 3-4-5 triangle
    
    def test_manhattan_distance_to_point(self):
        """Test Manhattan distance calculation to a point."""
        vectors = [Vector2(0, 0), Vector2(2, 3)]
        arr = VectorArray(vectors)
        target = Vector2(0, 0)
        
        distances = arr.manhattan_distance_to_point(target)
        assert distances.shape == (2,)
        assert distances[0] == 0
        assert distances[1] == 5  # |2-0| + |3-0|
    
    def test_filter_by_distance(self):
        """Test filtering by distance range."""
        vectors = [Vector2(0, 0), Vector2(1, 1), Vector2(2, 2)]
        arr = VectorArray(vectors)
        center = Vector2(0, 0)
        
        # Filter for distance 1-2 (Manhattan)
        filtered = arr.filter_by_distance(center, 1, 2)
        
        assert len(filtered) == 1
        assert filtered[0] == Vector2(1, 1)  # Manhattan distance = 2
    
    def test_filter_by_bounds(self):
        """Test filtering by rectangular bounds."""
        vectors = [Vector2(0, 0), Vector2(1, 1), Vector2(3, 3)]
        arr = VectorArray(vectors)
        
        # Filter for bounds 0-2 in both dimensions
        filtered = arr.filter_by_bounds(0, 2, 0, 2)
        
        assert len(filtered) == 2
        result_vectors = filtered.to_vector_list()
        assert Vector2(0, 0) in result_vectors
        assert Vector2(1, 1) in result_vectors
        assert Vector2(3, 3) not in result_vectors
    
    def test_contains(self):
        """Test vector containment checking."""
        vectors = [Vector2(1, 2), Vector2(3, 4)]
        arr = VectorArray(vectors)
        
        assert arr.contains(Vector2(1, 2))
        assert arr.contains(Vector2(3, 4))
        assert not arr.contains(Vector2(5, 6))
    
    def test_unique(self):
        """Test duplicate removal."""
        vectors = [Vector2(1, 2), Vector2(3, 4), Vector2(1, 2)]
        arr = VectorArray(vectors)
        
        unique = arr.unique()
        
        assert len(unique) == 2
        unique_vectors = unique.to_vector_list()
        assert Vector2(1, 2) in unique_vectors
        assert Vector2(3, 4) in unique_vectors
    
    def test_from_ranges(self):
        """Test creation from coordinate ranges."""
        arr = VectorArray.from_ranges((0, 2), (1, 3))
        
        # Should contain all combinations: (0,1), (0,2), (0,3), (1,1), (1,2), (1,3), (2,1), (2,2), (2,3)
        assert len(arr) == 9
        
        vectors = arr.to_vector_list()
        assert Vector2(0, 1) in vectors
        assert Vector2(2, 3) in vectors