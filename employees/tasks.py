import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from clients.models import Client
from api_config.models import SyncLog
from .services import APIService

User = get_user_model()
logger = logging.getLogger(__name__)

@shared_task
def sync_employees_task(user_id, client_id, sync_log_id=None):
    """Task for async employee synchronization"""
    logger.info(f"Starting employee sync: user={user_id}, client={client_id}, log={sync_log_id}")
    
    try:
        user = User.objects.get(id=user_id)
        client = Client.objects.get(id=client_id)
        
        # Call sync service with the log ID
        result = APIService.sync_employees(user, client, sync_log_id)
        
        logger.info(f"Employee sync completed: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Error in employee sync task: {str(e)}")
        
        # Update the log in case of error
        if sync_log_id:
            try:
                sync_log = SyncLog.objects.get(id=sync_log_id)
                sync_log.error_message = f"Error in synchronization: {str(e)}"
                sync_log.end_time = timezone.now()
                sync_log.status = 'error'
                sync_log.save()
            except Exception as log_error:
                logger.error(f"Error updating log: {str(log_error)}")
                
        return {
            "success": False,
            "message": f"Error in synchronization: {str(e)}"
        }

@shared_task
def sync_absences_task(user_id, client_id, sync_log_id=None):
    """Task for async absence synchronization"""
    logger.info(f"Starting absence sync: user={user_id}, client={client_id}, log={sync_log_id}")
    
    try:
        user = User.objects.get(id=user_id)
        client = Client.objects.get(id=client_id)
        
        # Call sync service with the log ID
        result = APIService.sync_absences(user, client, sync_log_id)
        
        logger.info(f"Absence sync completed: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Error in absence sync task: {str(e)}")
        
        # Update the log in case of error
        if sync_log_id:
            try:
                sync_log = SyncLog.objects.get(id=sync_log_id)
                sync_log.error_message = f"Error in synchronization: {str(e)}"
                sync_log.end_time = timezone.now()
                sync_log.status = 'error'
                sync_log.save()
            except Exception as log_error:
                logger.error(f"Error updating log: {str(log_error)}")
                
        return {
            "success": False,
            "message": f"Error in synchronization: {str(e)}"
        }