from .routing import explicit_route as r, domain_owner_authorization as domain_owner_authz
from .. import images as img

r('/source-images', img.post_source_image, methods=['POST'], expects_files=['image'],
       expects_domain=True, authorize=domain_owner_authz)
r('images', img.get_images, expects_domain=True, expects_params=True,
       authorize=domain_owner_authz)
#r('/source-images/<image_id>', img.get_source_image, expects_domain=True)
r('/images/<image_id>', img.get_image, expects_domain=True)
r('/products/<product_id>/images', img.get_product_images, expects_domain=True,
       authorize=domain_owner_authz, expects_params=True)
r('/products/<product_id>/images', img.put_product_images, methods=['PUT'], expects_domain=True, expects_data=True, authorize=domain_owner_authz)
r('/source-images-meta', img.post_source_image_meta, methods=['POST'], expects_data=True)
