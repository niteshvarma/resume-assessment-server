import ssl
from celery import Celery
from genfoundry.config import get_redis_config_dict


# def make_celery(config):
#     redis_host = config['REDIS_HOST']
#     redis_port = config['REDIS_PORT']
#     redis_password = config.get('REDIS_PASSWORD')
#     redis_ssl = config.get('REDIS_SSL', True)
#     redis_ssl_cert_reqs = config.get('REDIS_SSL_CERT_REQS', 'required')
#     redis_ssl_ca_certs = config.get('REDIS_SSL_CA_CERTS', None)

#     # Log configuration values for debugging
#     logger.debug(f"Redis Config - Host: {redis_host}, Port: {redis_port}, SSL: {redis_ssl}")
#     logger.debug(f"Redis Password: {redis_password}")
#     logger.debug(f"SSL Cert Reqs: {redis_ssl_cert_reqs}, SSL CA Certs: {redis_ssl_ca_certs}")

#     protocol = 'rediss' if redis_ssl else 'redis'
    
#     # Build the Redis URL with SSL and other params
#     redis_url = f"{protocol}://"
#     if redis_password:
#         redis_url += f":{redis_password}@{redis_host}:{redis_port}/0"
#     else:
#         redis_url += f"{redis_host}:{redis_port}/0"

#     logger.debug(f"Redis URL: {redis_url}")
    
#     try:
#         # Celery instance
#         celery = Celery(
#             'resume_processor',
#             broker=redis_url,
#             backend=redis_url,
#         )

#         ssl_options = {
#             'ssl_cert_reqs': ssl.CERT_REQUIRED,
#             'ssl_ca_certs': redis_ssl_ca_certs,
#         }
        
#         # Update Celery configurations
#         celery.conf.update(
#             task_serializer='json',
#             result_serializer='json',
#             accept_content=['json'],
#             timezone='UTC',
#             enable_utc=True,
#             broker_use_ssl=ssl_options,
#             backend_use_ssl=ssl_options,  # 👈 ADD THIS
#         )
#         logger.debug("Celery app successfully created and configured.")
#         return celery
#     except Exception as e:
#         logger.error(f"Error while creating and configuring Celery: {e}")
#         raise e

def make_celery(config):
    redis_host = config['REDIS_HOST']
    redis_port = config['REDIS_PORT']
    redis_password = config.get('REDIS_PASSWORD')
    redis_ssl = config.get('REDIS_SSL', True)
    redis_ssl_cert_reqs = config.get('REDIS_SSL_CERT_REQS', 'required')
    redis_ssl_ca_certs = config.get('REDIS_SSL_CA_CERTS', None)

    # Log configuration values for debugging
    # logger.debug(f"Redis Config - Host: {redis_host}, Port: {redis_port}, SSL: {redis_ssl}")
    # logger.debug(f"Redis Password: {redis_password}")
    # logger.debug(f"SSL Cert Reqs: {redis_ssl_cert_reqs}")
    # logger.debug(f"SSL CA Certs: {redis_ssl_ca_certs}")

    protocol = 'rediss' if redis_ssl else 'redis'
    
    # Build the Redis URL with SSL and other params
    redis_url = f"{protocol}://"
    if redis_password:
        redis_url += f":{redis_password}@{redis_host}:{redis_port}/0"
    else:
        redis_url += f"{redis_host}:{redis_port}/0"
    
    # Add ssl_cert_reqs to the Redis URL
    redis_url += f"?ssl_cert_reqs={redis_ssl_cert_reqs}"

    # logger.debug(f"Redis URL: {redis_url}")
    
    try:
        # Celery instance
        celery = Celery(
            'resume_processor',
            broker=redis_url,
            backend=redis_url,
        )

        # Update Celery configurations
        celery.conf.update(
            task_serializer='json',
            result_serializer='json',
            accept_content=['json'],
            timezone='UTC',
            enable_utc=True,
        )

        # logger.debug("Celery app successfully created and configured.")
        return celery
    except Exception as e:
        # logger.error(f"Error while creating and configuring Celery: {e}")
        raise e


celery_app = make_celery(get_redis_config_dict())

import genfoundry.km.api.standardize.celery_resume_processor_task

# Setup logging
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Get the logger separately
logger = logging.getLogger('genfoundry')
logger.setLevel(logging.DEBUG)
