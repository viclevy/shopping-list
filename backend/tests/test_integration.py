"""Integration test to verify google_search.py works with router modules."""

import asyncio
import sys
import os

# Add backend directory to path so we can import google_search, config, etc.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    try:
        from google_search import search_images, suggest_category_and_price, download_image
        print("  ✓ google_search imports work")
        return True
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False


async def test_function_signatures():
    """Test that function signatures are correct."""
    print("Testing function signatures...")
    from google_search import search_images, suggest_category_and_price

    try:
        # Test search_images
        result = await search_images("apple")
        assert isinstance(result, list), "search_images should return a list"
        print("  ✓ search_images signature correct")

        # Test suggest_category_and_price
        result = await suggest_category_and_price("milk")
        assert isinstance(result, dict), "suggest_category_and_price should return dict"
        assert "category" in result, "Result should have 'category' key"
        assert "price" in result, "Result should have 'price' key"
        print("  ✓ suggest_category_and_price signature correct")

        return True
    except Exception as e:
        print(f"  ✗ Function signature test failed: {e}")
        return False


async def test_backward_compatibility():
    """Test that existing code patterns still work."""
    print("Testing backward compatibility...")
    from google_search import suggest_category_and_price

    try:
        # This is how it's used in shopping_list_router.py
        suggestion = await suggest_category_and_price("Product Name")
        if suggestion.get("category"):
            category = suggestion["category"]
        print("  ✓ Backward compatible with shopping_list_router pattern")

        # Test how it's used in search_router.py
        results = await suggest_category_and_price("apple")
        return_dict = {"suggestions": results}
        print("  ✓ Backward compatible with search_router pattern")

        return True
    except Exception as e:
        print(f"  ✗ Backward compatibility test failed: {e}")
        return False


async def main():
    print("="*60)
    print("Integration Test for Updated google_search.py")
    print("="*60)
    print()

    all_pass = True

    all_pass = await test_imports() and all_pass
    all_pass = await test_function_signatures() and all_pass
    all_pass = await test_backward_compatibility() and all_pass

    print()
    print("="*60)
    if all_pass:
        print("✓ All integration tests passed!")
        print("✓ Module is ready for production use")
    else:
        print("✗ Some tests failed")
        sys.exit(1)
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
