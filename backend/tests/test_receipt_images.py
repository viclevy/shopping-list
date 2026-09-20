import os

import pytest
from PIL import Image

import photo_utils
from helpers import jpeg


def saved_image(filename):
    return Image.open(os.path.join(photo_utils.RECEIPT_DIR, filename))


def test_phone_rotation_is_applied():
    # EXIF orientation 6 means "rotate 90 degrees"; the saved photo must be upright for the AI to read
    filename = photo_utils.save_receipt_image(jpeg(400, 800, orientation=6))
    assert saved_image(filename).size == (800, 400)


def test_big_photos_are_scaled_down():
    filename = photo_utils.save_receipt_image(jpeg(5000, 6000))
    assert max(saved_image(filename).size) == photo_utils.RECEIPT_MAX_DIM


def test_something_that_is_not_an_image_is_refused():
    with pytest.raises(ValueError):
        photo_utils.save_receipt_image(b"not an image")


def test_receipt_photos_are_kept_outside_the_public_uploads_folder():
    filename = photo_utils.save_receipt_image(jpeg())
    assert os.path.dirname(os.path.join(photo_utils.RECEIPT_DIR, filename)) != photo_utils.UPLOAD_DIR
    assert not os.path.exists(os.path.join(photo_utils.UPLOAD_DIR, filename))
