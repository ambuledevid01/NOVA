from django.shortcuts import render , redirect 
from django.http import HttpResponse
from django.contrib.auth.models import User 
from django.contrib import messages 
from django.contrib.auth import login,logout , authenticate

## Login page 
def login_page(request) : 
    if request.method == "POST" :
        username = request.POST.get('username') 
        password = request.POST.get('password')

        user = User.objects.filter(username=username)
        
        # if user not exist 
        if not user.exists() : 
            messages.info(request , "User Not Exist, Register! ")
            return redirect('/login/')

        # if user exist but wrong pass word authentication return None 
        user_auth = authenticate(username =username , password=password )
        if not user_auth : 
            messages.error(request , " Wrong Username or Password  ")
            return redirect("/login/")
        
        # if authentication done 
        else : 
            login(request ,user = user_auth)
            return redirect('/Stream/dashboard_page/')   # whenver redirect the app url from project file use the name of the url or use the complete path of the url 
                                                    # like /Stream/dashboard 
    return render (request,'login.html')

# Register page 
def register_page(request) : 
    if request.method == "POST" : 
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        username = request.POST.get('username') 
        password = request.POST.get('password')

        user = User.objects.filter(username=username) 
        if user.exists() : 
            messages.info(request,'Username exists , Login !')
            return redirect('/register/')
    
        user = User.objects.create_user( 
             first_name = firstname , 
             last_name = lastname , 
             username = username , 
        )
        user.set_password(password) 

        user.save() 
        
        messages.info(request,"Account created successfully")
        return redirect('/register/')

    return render(request,'register.html')

def logout_page(request) : 
    logout(request)
    return  redirect('home_page')

def demo(request) : 
    return render(request,'demo.html')

def user_guide(request) : 
    return render(request , 'user_guide.html')

def home_page(request) : 
    return render(request, 'home.html')