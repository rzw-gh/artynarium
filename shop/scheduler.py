# from apscheduler.schedulers.background import BackgroundScheduler
# from django.core.exceptions import ObjectDoesNotExist
# from django.conf import settings
# from datetime import datetime, timedelta
# from . import models
# import time
#
#
# def delete_order(order_id, scheduler, job_id):
#     try:
#         order = models.Order.objects.get(orderid=order_id)
#         if order.status == 'Payment':
#             order_items = models.OrderItem.objects.filter(order=order)
#             for orderItem in order_items:
#                 product = models.Product.objects.get(id=orderItem.product.id)
#                 if orderItem.from_store_amount:
#                     product.store_amount += orderItem.quantity
#                     product.save()
#                 if orderItem.from_amount:
#                     product.amount += orderItem.quantity
#                     product.save()
#                 if orderItem.product.variant != 'None':
#                     variant = models.Variants.objects.get(id=orderItem.variant.id)
#                     if orderItem.from_store_amount:
#                         variant.quantity += orderItem.quantity
#                         variant.save()
#                     if orderItem.from_amount:
#                         variant.seller_quantity += orderItem.quantity
#                         variant.save()
#             order.status = 'Canceled'
#             order.save()
#             user_coupon_usage = models.UserCouponUsage.objects.filter(user=order.user, coupon=order.coupon)
#             if user_coupon_usage.exists():
#                 user_coupon_usage = models.UserCouponUsage.objects.get(user=order.user, coupon=order.coupon)
#                 user_coupon_usage.used = False
#                 user_coupon_usage.save()
#                 coupon = models.Coupon.objects.get(code=order.coupon.code)
#                 coupon.usage_count -= 1
#                 coupon.save()
#             if models.SchedulerJobs.objects.filter(id=job_id).exists():
#                 job_obj = models.SchedulerJobs.objects.get(id=job_id)
#                 job_obj.status = 'Completed'
#                 job_obj.save()
#             print("Order Canceled Successfully")
#             print("Removing Job ", job_id, " ...")
#             scheduler.remove_job(job_id=str(job_id))
#             print("Job Removed Successfully with id ", job_id)
#             print("Stopping Scheduler...")
#             scheduler.shutdown(wait=False)
#             print("Scheduler turned off successfully!")
#     except ObjectDoesNotExist:
#         print("Removing Job ", job_id, " ...")
#         scheduler.remove_job(job_id=str(job_id))
#         print("Job Removed Successfully with id ", job_id)
#         print("Stopping Scheduler...")
#         scheduler.shutdown(wait=False)
#         print("Scheduler turned off successfully!")
#
#
# def delete_order_job(order_id, sec=3600, check=False, job_id=''):
#     if check:
#         scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
#         try:
#             if scheduler.get_job(job_id=str(job_id)):
#                 scheduler.remove_job(job_id=str(job_id))
#             scheduler.add_job(
#                 delete_order,
#                 'interval',
#                 seconds=sec,
#                 id=str(job_id),
#                 kwargs={'order_id': order_id, 'scheduler': scheduler, 'job_id': job_id},
#                 replace_existing=True
#             )
#             print('Job Created/on server reboot')
#             try:
#                 print("Starting Scheduler...")
#                 scheduler.start()
#                 print('Scheduler Started')
#             except Exception as e:
#                 print("Stopping Scheduler...")
#                 scheduler.shutdown()
#                 print("Scheduler turned off successfully!")
#                 print('error caused by: '+str(e))
#         except Exception as e:
#             print(e)
#     else:
#         scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
#         try:
#             job_obj = models.SchedulerJobs()
#             job_obj.order_id = order_id
#             job_obj.type = 'Order'
#             job_obj.save()
#             scheduler.add_job(
#                 delete_order,
#                 'interval',
#                 seconds=sec,
#                 id=str(job_obj.id),
#                 kwargs={'order_id': order_id, 'scheduler': scheduler, 'job_id': job_obj.id},
#                 replace_existing=True
#             )
#             print('Job Created')
#             try:  # Start Scheduler
#                 print("Starting Scheduler...")
#                 scheduler.start()
#                 print('Scheduler Started')
#             except Exception as e:
#                 print("Stopping Scheduler...")
#                 scheduler.shutdown()
#                 print("Scheduler turned off successfully!")
#                 print('error caused by: '+str(e))
#         except Exception as e:
#             print(e)
#
#
# def delete_cart(cart_id, scheduler, job_id):
#     try:
#         cart = models.Cart.objects.get(id=cart_id)
#         product = models.Product.objects.get(id=cart.product.id)
#         if cart.from_store_amount:
#             product.store_amount += cart.quantity
#             product.save()
#         if cart.from_amount:
#             product.amount += cart.quantity
#             product.save()
#         if cart.variant:
#             variant = models.Variants.objects.get(id=cart.variant.id)
#             if cart.from_store_amount:
#                 variant.quantity += cart.quantity
#                 variant.save()
#             if cart.from_amount:
#                 variant.seller_quantity += cart.quantity
#                 variant.save()
#         cart_limit_lists = models.CartLimit.objects.filter(cart=cart)
#         if len(cart_limit_lists) > 1:
#             for cl in cart_limit_lists:
#                 cl.delete()
#             cart.delete()
#         else:
#             cart_limit = models.CartLimit.objects.get(cart=cart)
#             cart_limit.delete()
#             cart.delete()
#         if models.SchedulerJobs.objects.filter(id=job_id).exists():
#             job_obj = models.SchedulerJobs.objects.get(id=job_id)
#             job_obj.status = 'Completed'
#             job_obj.save()
#     except ObjectDoesNotExist:
#         print("Removing Job ", job_id, " ...")
#         scheduler.remove_job(job_id=str(job_id))
#         print("Job Removed Successfully with id ", job_id)
#         print("Stopping Scheduler...")
#         scheduler.shutdown(wait=False)
#         print("Scheduler turned off successfully!")
#
#
# def delete_cart_job(cart_id, sec=3600, check=False, job_id=''):
#     scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
#     if check:
#         try:
#             if scheduler.get_job(job_id=str(job_id)):
#                 scheduler.remove_job(job_id=str(job_id))
#             scheduler.add_job(
#                 delete_cart,
#                 'interval',
#                 seconds=sec,
#                 id=str(job_id),
#                 kwargs={'cart_id': cart_id, 'scheduler': scheduler, 'job_id': job_id},
#                 replace_existing=True
#             )
#             print('Job Created/on server reboot')
#             try:
#                 print("Starting Scheduler...")
#                 scheduler.start()
#                 print('Scheduler Started')
#             except Exception as e:
#                 print("Stopping Scheduler...")
#                 scheduler.shutdown()
#                 print("Scheduler turned off successfully!")
#                 print('error caused by: '+str(e))
#         except Exception as e:
#             print(e)
#     else:
#         try:
#             job_obj = models.SchedulerJobs()
#             job_obj.cart_id = cart_id
#             job_obj.type = 'Cart'
#             job_obj.save()
#             scheduler.add_job(
#                 delete_cart,
#                 'interval',
#                 seconds=sec,
#                 id=str(job_obj.id),
#                 kwargs={'cart_id': cart_id, 'scheduler': scheduler, 'job_id': job_obj.id},
#                 replace_existing=True
#             )
#             print('Job Created')
#             try:
#                 print("Starting Scheduler...")
#                 scheduler.start()
#                 print('Scheduler Started')
#             except Exception as e:
#                 print("Stopping Scheduler...")
#                 scheduler.shutdown()
#                 print("Scheduler turned off successfully!")
#                 print('error caused by: '+str(e))
#         except Exception as e:
#             print(e)
#
#
# def on_server_reboot_check_jobs():
#     print('on_server_reboot_check_jobs '+str(datetime.now())+'\n')
#     incomplete_jobs = models.SchedulerJobs.objects.filter(status='Processing')
#     if incomplete_jobs.exists():
#         for job in incomplete_jobs:
#             try:
#                 an_hour_after_create_time = job.create_at + timedelta(hours=1)
#                 print('an_hour_after_create_time: '+str(an_hour_after_create_time))
#                 if datetime.now(job.create_at.tzinfo) >= an_hour_after_create_time:
#                     print('yes bigger ' + str(job.order_id))
#                     if job.type == 'Order':
#                         delete_order_job(job.order_id, 5, True, job.id)
#                         print('Order-b done!')
#                     elif job.type == 'Cart':
#                         print('Cart-b done!')
#                         delete_cart_job(job.cart_id, 5, True, job.id)
#                 else:
#                     print('no smaller ' + str(job.order_id))
#                     remaining_time = an_hour_after_create_time - datetime.now(job.create_at.tzinfo)
#                     print('remaining_time: '+str(remaining_time))
#                     remaining_time = time.mktime(remaining_time.timetuple()) + remaining_time.microsecond/1e6
#                     if job.type == 'Order':
#                         print('Order-s done!')
#                         delete_order_job(job.order_id, remaining_time, True, job.id)
#                     elif job.type == 'Cart':
#                         print('Cart-s done!')
#                         delete_cart_job(job.cart_id, remaining_time, True, job.id)
#             except Exception as e:
#                 print(e)
