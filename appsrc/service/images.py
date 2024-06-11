import hashlib
import os
from flask import current_app as app
from sqlalchemy.orm import exc as orm_exc
from werkzeug.utils import secure_filename
from libthumbor import CryptoURL

from . import errors as err
from .validation import images as vld
from ..db import db
from ..db.models import images as img

imgcnf = lambda: app.config.IMAGE

def load_image_from_filepath(filepath):
    # service
    """
    Return image associated with record.
    """
    try:
        return img.ImageUtil.load_from_filepath(filepath, imgcnf())
    except:
        raise err.NotFound('Image not found')

def get_main_image_record(source_record):
    """
    Fetch main image record if exists.
    """
    try:
        return next(c for c in source_record.copies if c.name=='main')
    except StopIteration:
        raise err.NotFound('Main image not found')

def delete_image_record(record):
    # delete file
    try:
        os.unlink(record.meta.get('filepath'))
        db.session.delete(record)
    except: pass

def generate_main_copy(source_record):
    # service
    config = imgcnf()
    main_record = None
    try:
        # First, try returning existing copy.
        main_record = get_main_image_record(source_record)
        _ = load_image_from_filepath(main_record.meta.get('filepath')) # Check file exists.
        return main_record
    except:
        # Whatever the problem delete that record if it exists.
        if main_record: delete_image_record(main_record)
    # No existing copy. Generate one.
    try:
        source_image = load_image_from_filepath(source_record.meta.get('filepath'), config)
        main_copy = source_image.thumbnail(config['WEB_MAX_LENGTH'], context='web')
        main_copy.save()
        main_record = img.BaseImage(
            domain_id = source_record.domain_id,
            base_image_id = main_copy.blob_signature,
            meta = {**main_copy.datadict},
            source=source_record, )
        set_aspect_ratios(main_record)
        db.session.add(main_record)
        db.session.flush()
    except:
        db.session.rollback()
        raise err.FormatError('Could not copy source image')
    return main_record

def _file_basename(file):
        try:
            # First, try to use as werkzeug.datastructures.FileStorage.
            fn = file.filename
        except AttributeError:
            try:
                # Then try as file object.
                fn = file.name
            except AttributeError:
                fn = None
        return secure_filename(os.path.basename(fn)) if fn else None

def save_source_image(domain_id, source_file):
    # service
    config = imgcnf()
    try:
        source_image = img.ImageUtil.load_from_file(source_file, config, context='source')
    except:
        raise err.FormatError('Could not load image file')
    try:
        # First, try returning existing image record.
        image_id = source_image.blob_signature
        return get_source_image_record(image_id, domain_id)
    except err.NotFound as e:
        pass
    try:
        # No existing record. Create one.
        meta = {**source_image.datadict}
        meta['original_name'] = _file_basename(source_file)
        source_image.save()
        source_record = img.SourceImage(
            source_image_id=image_id,
            domain_id=domain_id,
            meta=meta, )
        db.session.add(source_record)
        db.session.flush()
    except:
        db.session.rollback()
    return source_record

def get_images(domain_id):
    # service
    return img.BaseImage.query.filter_by(domain_id=domain_id).all()

def _filter_aspect_ratios(original_aspect_ratios, original_sizes, params):
    # service
    rv = [original_aspect_ratios, original_sizes]
    try:
        params = vld.aspect_ratios.validate(params)
    except:
        raise err.FormatError('Invalid aspect ratio or size format')
    try:
        valid_ratios = params['aspect_ratios']
        valid_sizes = params['sizes']
    except KeyError:
        raise err.FormatError('Missing "aspect_ratios" or "sizes" key in params')
    if valid_ratios:
        rv[0] = tuple(ar for ar in rv[0] if ar['name'] in valid_ratios)
    if valid_sizes:
        rv[1] = tuple(s for s in rv[1] if s[0] in valid_sizes)
    return rv

def get_aspect_ratios(image, filter_params=None):
    # service
    img_meta = image.meta
    # TODO: get this from config
    crypto = CryptoURL(key='MY_SECURE_KEY')
    # TODO: get this from config
    img_sizes = tuple(
        s for s in (('large',0), ('medium',700), ('small',300), ('thumb',100)))
    # add '0:0' to image's stored aspect ratios
    img_aspect_ratios = tuple(
        ar for ar in [{'name':'0:0'}]+ img_meta.get( 'aspect_ratios', []))
    if filter_params:
        img_aspect_ratios, img_sizes = _filter_aspect_ratios(
            img_aspect_ratios, img_sizes, filter_params)
    # determine the widest side
    largest = 'width' if img_meta.get('width', 0)>=img_meta.get('height', 0) else 'height'
    thumbor_base = app.config['THUMBOR_SERVER']
    base_options = {"image_url": img_meta['filename']}
    rv = {}
    for a_r in img_aspect_ratios:
        crop = None
        if a_r['name']!='0:0':
            ab = (a_r['A'], a_r['B'])
            cd = (a_r['C'], a_r['D'])
            crop = ab, cd
        #for size_name, size in valid_sizes():
        for size_name, size in img_sizes:
            b_o = {**base_options}
            # If a_r is not 0:0 (i.e. original size) it means there's some cropping to do.
            if crop:
                b_o['crop'] = crop
            if size:
                b_o[largest] = min(size, a_r.get(largest, img_meta[largest]))
            try:
                url = crypto.generate(**b_o)
            except Exception as e:
                # TODO: log problem and set url to placeholder image
                url = ""
            rv.setdefault(a_r['name'], {})[size_name] = f'{thumbor_base}{url}'
    return rv

def get_image(image_id, domain_id, params):
    # service
    try:
        return img.BaseImage.query.get((image_id, domain.domain_id))
    except orm_exc.NoResultFound as e:
        raise err.NotFound('Image not found')

def get_product_images(product_id, domain_id):
    # service
    rv = img.ProductImage.query.filter_by(
        product_id=product_id, domain_id=domain_id).all()
    rv.sort(key=lambda pi: pi.data.get('position'))
    return rv

def update_product_images(product_id, domain_id, data):
    # service
    # TODO: Possible optimization possible, depending how this is being used.
    # TODO: delete where (product_id, image_id) not IN (
    #   (:dom_id, :prod_id, :img_id), (:dom_id, :prod_id, :img_id) )
    db.session.execute(db.text(
        'delete from product_images '
        'where product_id=:product_id and domain_id=:domain_id'
    ), {'product_id': product_id, 'domain_id': domain_id})
    #TODO: validation
    for position, image_id in enumerate(data):
        db.session.add(img.ProductImage(
            domain_id=domain_id,
            product_id=product_id,
            base_image_id=image_id,
            data={'position':position}))
    db.session.flush()

# NOTE: might not be useful
def save_source_image_data(data):
    # service
    data = add_source_image.validate(data)
    source_image = img.SourceImage(**data)
    try:
        db.session.add(source_image)
        db.session.flush()
    except orm_exc.IntegrityError:
        raise err.FormatError('Could not update source image data')
    return source_image

def get_source_image_record(image_id, domain_id):
    # service
    try:
        return img.SourceImage.query.filter_by(
            source_image_id=image_id, domain_id=domain_id).one()
    except orm_exc.NoResultFound as e:
        raise err.NotFound('Image not found')

def crop_to_aspect_ratio(aspect_ratio, current):
    # service
    ar = [int(i) for i in aspect_ratio.split(':')]
    rv = dict(name=aspect_ratio)
    horizontal = current['width']>=current['height']
    target = {}
    # calculate the goal ratio
    target_ratio = ar[0]/ar[1]
    if horizontal:
        width, height, a,b,c,d = 'width', 'height', 'A','B','C','D'
    # flip coordinates if vertical
    else:
        width, height, a,b,c,d = 'height', 'width', 'B','A','D','C'
    current_ratio = current[width]/current[height]
    crop = {}
    # calculate the difference to crop
    if target_ratio > current_ratio:
        # cropping height
        target[width] = current[width]
        target[height] = current[width]/target_ratio
        crop[a] = 0
        crop[b] = (current[height] - target[height])/2
        crop[c] = target[width]
        crop[d] = crop[b] + target[height]
    else:
        # cropping width
        target[height] = current[height]
        target[width] = current[height] * target_ratio
        crop[a] = (current[width] - target[width])/2
        crop[b] = 0
        crop[c] = crop[a] + target[width]
        crop[d] = target[height]
    rv.update({k:int(round(float(v))) for k,v in crop.items()})
    rv[width] = int(round(target[width]))
    rv[height] = int(round(target[height]))
    rv['AxB'] = f'{rv[a]}x{rv[b]}'
    rv['CxD'] = f'{rv[c]}x{rv[d]}'
    rv['AxB:CxD'] = f'{rv["AxB"]}:{rv["CxD"]}'
    return rv

def set_aspect_ratios(base_image):
    # service
    aspect_ratios = ('1:1', '5:4', '4:3', '3:2', '16:9', '3:1')
    base_image.meta['aspect_ratios'] = [
        crop_to_aspect_ratio(ar, base_image.meta) for ar in aspect_ratios]
