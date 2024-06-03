from PIL import Image as pilimage
from uuid import uuid4
import io
from contextlib import contextmanager
import os
import hashlib
import weakref
from werkzeug.utils import secure_filename

from . import db

class SourceImage(db.DomainMixin, db.Model,):
    """
    Image uploaded to the server and used later as source to generate derivative base
    image copies (accessible via the `copies` relation).
    """

    __abstract__ = False
    __tablename__ = 'source_images'

    # source_image_id will be the blob's signature which is a sha1 hash of the
    # file's contents.
    source_image_id = db.Column(db.Unicode, primary_key=True)
    meta = db.Column(db.JSONB)
    """ {
        "filename": <filename>,
        "filesize" : <size>,
        "path" : <size>,
        "width" : <width>,
        "height" : <height>,
        "content_type" : <content_type>,
        "original_name": <original_name>, # might never be useful
    } """

class BaseImage(db.DomainMixin, db.Model):
    """
    Compressed and/or resized copy of an original source image.
    Two types of copies:
    - main:
        - should ideally be unique.
        - compressed version of uploaded source image.
        - no cropping, only resizing (dimensions and bytes).
    - others:
        - useful when a specific region of the uploaded source is desired.
    Aspect ratios are calculated for all types.
    """

    __abstract__ = False
    __tablename__ = 'base_images'

    base_image_id = db.Column(db.Unicode, primary_key=True)
    source_image_id = db.Column(None)
    name = db.Column(db.Unicode, nullable=False, default='main')
    meta = db.Column(db.JSONB)
    """ {
        "filename": <filename>,
        "signature": <signature>,
        "filesize" : <size>,
        "path" : <size>,
        "width" : <width>,
        "height" : <height>,
        "content_type" : <content_type>,
        "webpath" : <webpath>,
        "aspect_ratios" : [
            {
                "name": "1:1",
                "A": 0, "B": 5, "C": 300, "D": 305,
                "AxB": "0x5, "CxD": "300x305",
                "AxB:CxD": "0x5:300x305",
            },
        ]
    } """

    __table_args__ = (
        db.ForeignKeyConstraint(
            [source_image_id, 'domain_id'],
            ['source_images.source_image_id', 'source_images.domain_id'],),
        db.UniqueConstraint('domain_id', 'source_image_id', 'name'),)

    # relationships
    source = db.relationship('SourceImage', backref='copies')

class ProductImage(db.DomainMixin, db.Model):
    """
    Base image specifically associated with a product. It must have been previously added
    to the image collection.
    Each ProductImage relation has its own metadata (`data`).
    """
    __abstract__ = False
    __tablename__ = 'product_images'

    product_image_id = db.Column(db.UUID, primary_key=True, default=uuid4)
    product_id = db.Column(None)
    base_image_id = db.Column(None)
    data = db.Column(db.JSONB)
    """ {
            "position": 1,
            "en" : {
                "title" : null,
                "caption" : null,
                "caption_html" : null,
                "label" : null,
                "seo_title" : null,
                "remote_url" : null,
            },...
    } """

    __table_args__ = (
        db.ForeignKeyConstraint(
            [product_id, 'domain_id'], ['products.product_id', 'products.domain_id']),
        db.ForeignKeyConstraint(
            [base_image_id, 'domain_id'],
            ['base_images.base_image_id', 'base_images.domain_id']),)

    image = db.relationship('BaseImage', backref="products", viewonly=True)
    product = db.relationship('Product', backref="images")

class ImageUtil:
    """
    Unify file object and PIL interfaces and integrate with local storage scheme as
    enforced by the config object. Provide additional validating functions.
    """

    def __init__(self, byte_content, config, context):
        """
        It's better to use one of the classmethod constructors than to use this directly.

        @param: config
        dict object expected with the following keys:
            - ASPECT_RATIO : dict containing vertical and horizontal aspect ratio
            constraints. I.e. minimal ratio for vertical images and maximal ratio
            for horizontal images.
            - DUMP : base path to image dump. A context may be affixed to it, if one is
            provided.
            - SUPPORTED_FORMATS : dict of supported image formats as it's specified by PIL.

                >>> print(pil_object.format)
                PNG

            - MAX_FILESIZE : the file size in bytes.
            - WEB_MAX_LENGTH :

        @param: context
        The context is used when saving the image on the file system. It indicates how
        the file is going to be used. Examples of contexts are 'source' and 'web', which
        respectively point to the original source copy and the resized/compressed copies.

            /path/to/image
                /source
                    /original_copy.png
                /web
                    /resized_copy.png
                    /compressed_copy.png
                    /...
        When loading an image from its filepath, if a context is not specified, it's
        inferred from the path (see `_infer_context_from_filepath()` method). This is
        recommended, unless you want to make a copy of the file in a different context.
        """
        self.byte_content = byte_content
        self.config = config
        self.context = context or ''
        self.validate_format()
        self.validate_aspect_ratio()

    @classmethod
    def load_from_file(cls, file, config, context=None):
        """
        This constructor uses an image file. It's mostly useful for saving new image
        sources.
        """
        file.seek(0)
        byte_content = file.read()
        return ImageUtil(byte_content, config, context)

    @classmethod
    def load_from_filepath(cls, filepath, config, validate_filepath=True):
        """
        This constructor expects by default a filepath that is consistent with the storage
        scheme. That is, it expects the path to lead to an image that was saved using
        this utility or that emulated the scheme. To disable this constraint, unset
        `validate_filepath`.
        """
        with open(filepath, 'rb') as file_object:
            instance = cls.load_from_file(file_object, config, context=None)
        if validate_filepath:
            instance.validate_filepath(filepath):
            # Override context
            instance.context = instance._infer_context_from_filepath(filepath)
        return instance

    @property
    def pil_object(self):
        if not getattr(self, '_pil_object', None):
            with self.file_object() as file:
                try:
                    self._pil_object = pilimage.open(file)
                except IOError as e:
                    # TODO: make this part of validation
                    raise Exception('Unrecognized image format')
         return self._pil_object

    @contextmanager
    def file_object(self)
        file = io.BytesIO()
        file.write(self.byte_content)
        yield file
        file.close()

    @property
    def filesize(self):
        return len(self.byte_content)

    @property
    def extension(self):
        if not getattr(self, '_extension', None):
            try:
                self._extension = self.config['SUPPORTED_FORMATS'][self.image_format]
            except KeyError:
                raise Exception('Unrecognized image format')
        return self._extension

    @property
    def blob_signature(self):
        """
        Identifier based on file content.
        """
        if not getattr(self, '_signature', None):
            self._signature = hashlib.sha1(self.byte_content).hexdigest()
        return self._signature

    @property
    def filename(self):
        if not getattr(self, '_filename', None):
            self._filename = '.'.join([self.blob_signature, self.extension])
        return self._filename

    @property
    def path_prefix(self):
        if not getattr(self, '_path_prefix', None):
            fn = self.filename
            self._path_prefix = '/'.join([fn[:2], fn[2:4]])
        return self._path_prefix

    @property
    def filepath(self):
        """
        The filepath is dependent on the context and filename. The filename itself
        depends on the byte content.
        """
        if not getattr(self, '_filepath', None):
            self._filepath = os.path.join(
                self.config['DUMP'],
                self.context,
                self.path_prefix,
                self.filename, )
        return self._filepath

    def _infer_context_from_filepath(self, filepath):
        start = len(self.config['DUMP'])
        end = filepath.index(self.path_prefix)
        if end - start < 1:
            return ''
        return filepath[start:end].strip('/')

    @property
    def image_format(self):
        return self.pil_object.format

    @property
    def width(self):
        return self.pil_object.width

    @property
    def height(self):
        return self.pil_object.height

    @property
    def datadict(self):
        if not getattr(self, '_data', None):
            self._data = {
                "format": self.image_format,
                "extension": self.extension,
                "width": self.width,
                "height": self.height,
                "filesize": self.filesize,
                "filename": self.filename,
                "filepath": self.filepath, }
        return self._data

    def validate_filepath(self, filepath):
        """
        Ensure that given path is consistent with image saving scheme.
        """
        err = lambda: IOError(
            "Invalid file image path. Try directly passing a file object "
            "to the `load_from_file` constructor.")
        if not filepath.startswith(self.config['DUMP']):
            raise err()
        if not filepath.endswith(os.path.join(self.path_prefix, self.filename)):
            raise err()

    def validate_format(self):
        if not self.image_format in self.config['SUPPORTED_FORMATS']:
            raise TypeError('Unsupported image format')

    def validate_aspect_ratio(self):
        """
        Ensure image is being treated within certain aspect ratio constraints.
        I.e. don't treat overly vertical or overly horizontal images.
        """
        width, height = self.pil_object.size
        aspect_ratio  = self.config['ASPECT_RATIO']
        if not (aspect_ratio['vertical'] <= width/height <= aspect_ratio['horizontal']):
            raise Exception('Unsupported aspect ratio')

    # TODO: should be applied at web server or middleware level
    def validate_filesize(self):
        if not self.filesize <= self.config['MAX_FILESIZE']:
            raise Exception('Image file is too large')

    def thumbnail(self, max_length=None, config=None, context=None):
        """
        A wrapper around PIL's `thumbnail` utility. Returns an `ImageUtil` instance.
        Create an image of the specified max_length, or less, on its largest side.
        If the max_length is larger than the largest of height and width on the source
        image, the latter is chosen as the size. Implying that this utility does not
        enlarge images.
        """
        max_length = max_length if max_length else self.config['WEB_MAX_LENGTH']
        config = config if config else self.config
        context = context if context else self.context
        def pil_action(pil_obj):
            size = min(max_length, max(pil_image.width, pil_image.height))
            pil_obj.thumbnail((size, size))
        return self.action_proxy(pil_action, config, context)

    def action_proxy(action_fnc, config=None, context=None):
        """
        Run action_fnc, passing it a copy of pil_object as first param.
        Return new ImageUtil with content of modified pil_object copy.
        See the thumbnail method for an example usage.
        """
        config = self.config if not config else config
        context = self.context if not context else context
        pil_object_copy = self.pil_object.copy()
        # We must set the format ourselves, PIL doesn't do it for image it creates.
        pil_object_copy.format = self.pil_object.format
        action_fnc(pil_object_copy)
        with io.BytesIO() as fh:
            pil_object_copy.save(fh, pil_object_copy.format)
            rv = ImageUtil.load_from_file(fh, config, context)
        return rv

    def save(self, destination=None):
        """
        Saves the original byte content, not the PIL processed images. To save modified
        PIL images instead, see `thumbnail` and `action_proxy` methods.
        """
        if destination is None:
            destination = self.filepath
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'wb') as f:
            f.write(self.byte_content)
