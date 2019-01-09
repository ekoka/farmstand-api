from PIL import Image as pilimage
import io
import contextlib
import os
import hashlib
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.sql.expression import case, ClauseElement
from sqlalchemy.ext.compiler import compiles
from  sqlalchemy.types import TypeDecorator
from werkzeug.utils import secure_filename

from . import db
from ..trigger import Trigger, TriggerProcedure
from ..view import view_mapper, create_view

class SourceImage(db.TenantMixin, db.Model,):
    """
    Images uploaded to the server and used later as source for product images.
    """
    __abstract__ = False
    __tablename__ = 'source_images'

    # source_image_id will be the blob's signature which is a sha1 hash of the
    # file's contents.
    source_image_id = db.Column(db.Unicode, primary_key=True) 
    meta = db.Column(db.JSONB)
    """ { 
        "original_name": <original_name>,
        "filename": <filename>,
        "filesize" : <size>,
        "path" : <size>,
        "width" : <width>,
        "height" : <height>,
        "content_type" : <content_type>,
    } """

class BaseImage(db.TenantMixin, db.Model):
    """
    Compressed copies of the original uploaded source.

    2 types of copies:
    - main: 
        - unique
        - simple compressed version of uploaded source image. 
        - no cropping, only resizing.
    - others: 
        - useful when a specific region of the uploaded source is desired.

    For both types, a set of aspect ratios are calculated.
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
            [source_image_id, 'tenant_id'], 
            ['source_images.source_image_id', 'source_images.tenant_id'],
        ),
        db.UniqueConstraint('tenant_id', 'source_image_id', 'name'),
    )

    source = db.relationship('SourceImage', backref='copies')




class ProductImage(db.TenantMixin, db.Model):
    """Images associated to a product. The image must first be added to the
    source image collection, via upload, if it's present on the user's local 
    machine, or via download, if it's on a remote server or cloud service.
    """
    __abstract__ = False
    __tablename__ = 'product_images'

    product_image_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(None)
    base_image_id = db.Column(None)
    data = db.Column(db.JSONB) # defaults to ImageFormat.data
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
        db.ForeignKeyConstraint([product_id, 'tenant_id'], 
                                ['products.product_id', 'products.tenant_id']),
        db.ForeignKeyConstraint(
            [base_image_id, 'tenant_id'], 
            ['base_images.base_image_id', 'base_images.tenant_id']
        ),
    )

class ImageUtil:
    """ Unify file and PIL.Image.Image interfaces and provide additional
    validating functions.
    """

    def __init__(self, image_file, config=None, context=None):
        if config is None:
            config = self._default_config()  
        self.config = config

        if context is None:
            context = ''
        self.context = context

        if isinstance(image_file, pilimage.Image):
            self._from_image(image_file)
        else:
            self._from_file(image_file)

        self.validate_format()
        self.validate_aspect_ratio()

    def _from_image(self, image):
        self.image = i = image
        self.image_file = image_file = io.BytesIO()
        i.save(image_file, format=i.format)

    def _from_file(self, image_file):
        if isinstance(image_file, str):
            image_file = open(image_file, 'rb')
        self.image_file = image_file
        try:
            self.image = pilimage.open(image_file)
        except IOError as e:
            # TODO: make this part of validation
            raise Exception('unrecognized image format')

    @property
    def original_name(self):
        if not getattr(self, '_original_name', None):
            try:
                # is this a werkzeug.datastructures.FileStorage
                filename = self.image_file.filename
            except AttributeError:
                try:
                    # or is it a file or BytesIO object
                    filename = self.image_file.name
                except AttributeError:
                    filename = None
            self._original_name = (secure_filename(filename) 
                                   if filename is not None else None)
        return self._original_name

    @property
    def filesize(self):
        if not getattr(self, '_filesize', None):
            with self.initfile(self.image_file) as f:
                f.seek(0, os.SEEK_END)
                self._filesize = f.tell()
        return self._filesize

    @property
    def extension(self):
        if not getattr(self, '_extension', None):
            try: 
                self._extension = self.config[
                    'SUPPORTED_FORMATS'][self.image.format]
            except KeyError:
                raise Exception('unrecognized image format')
        return self._extension

    @property
    def blob_signature(self):
        # an identifier based on the file's contents
        if not getattr(self, '_signature', None):
            content = self.read()
            self._signature = hashlib.sha1(content).hexdigest()
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
        if not getattr(self, '_filepath', None):
            self._filepath = os.path.join(
                self.config['DUMP'], 
                self.context,
                self.path_prefix,
                self.filename)
        return self._filepath

    @property
    def datadict(self):
        """ REDUNDANT: for documentation purposes mostly """
        if not getattr(self, '_data', None):
            self._data = dict(
                original_name=self.original_name, 
                format=self.image.format,
                extension=self.extension,
                width=self.image.width,
                height=self.image.height,
                filesize=self.filesize,
                filename=self.filename,
                filepath=self.filepath,
            )
        return self._data

    def _default_config(self):
        return dict(
            DUMP = '/tmp/simpleb2b/images',
            MAX_FILESIZE = 10000000, #10mb
            ASPECT_RATIO = (0.3333, 3.0),
            WEB_MAX_LENGTH = 900, # max width/height length
            SUPPORTED_FORMATS = dict(
                JPEG='jpg',
                JPG='jpg',
                PNG='png',
                GIF='gif',
            )
        )


    def validate_format(self):
        if not self.image.format in self.config['SUPPORTED_FORMATS']:
            raise TypeError('unsupported image format')

    def validate_aspect_ratio(self):
        width, height = self.image.size
        aspect_ratio  = self.config['ASPECT_RATIO']
        if not (aspect_ratio[0] <= width/height <= aspect_ratio[1]):
            raise Exception('unsupported aspect ratio')

    # TODO: should be applied at web server or middleware level
    def validate_filesize(self):
        if not self.filesize <= self.config['MAX_FILESIZE']:
            raise('image file too large')

    def thumbnail(self, max_length=None, config=None, context=None):
        if max_length is None:
            max_length = self.config['WEB_MAX_LENGTH']
        if config is None:
            config = self.config
        if context is None:
            context = self.context

        source = self.image
        web_size = min(max_length, max(source.width, source.height))
        web_image = source.copy()
        # we must set the format ourselves, PIL doesn't do it for image
        # it creates.
        web_image.format = source.format
        web_image.thumbnail((web_size, web_size))
        return ImageUtil(web_image, config=config, context=context)

    def read(self):
        f = self.image_file
        with self.initfile(self.image_file) as f:
            rv = f.read()
        return rv

    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, 'wb') as f:
            f.write(self.read())

    @contextlib.contextmanager
    def initfile(self, f):
        pos = f.tell()
        f.seek(0)
        yield f
        f.seek(pos)
        

    

