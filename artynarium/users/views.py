from django.shortcuts import redirect


def login_success(request):
    if request.user.seller:
        print('seller here')
        return redirect('seller:order')
    else:
        print('ordinary here')
        return redirect('shop:my_orders')
