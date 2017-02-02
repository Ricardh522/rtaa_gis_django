from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.renderers import TemplateHTMLRenderer
from django.template.response import TemplateResponse
from rest_framework.response import Response
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework.permissions import AllowAny
from .utils.ldap_tool import LDAPQuery
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Group
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
import logging

logger = logging.getLogger(__package__)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class HomePage(APIView):
    """View that renders the opening homepage"""
    renderer_classes = (TemplateHTMLRenderer,)
    permission_classes = (AllowAny,)
    template = r'home/home_body.html'

    def get(self, request, format=None):
        if not request.user.is_authenticated():
            return redirect(reverse('home:login'))
        try:
            name = request.META['REMOTE_USER']
        except KeyError:
            name = request.user.username

        # for dev with dojo, if username is '', set it to siteadmin
        if name == '':
            name = 'siteadmin'

        resp = Response(template_name=self.template)
        resp['Cache-Control'] = 'no-cache'

        # Perform inheritance from AD
        query = LDAPQuery(name, 'gisapps.aroraengineers.com')
        ldap_groups = query.get_groups()
        logger.info("ldap_groups = {}".format(ldap_groups))

        user_obj = User.objects.get(username=name)
        users_groups = user_obj.groups.all()
        # remove groups from user if not in LDAP group list
        for x in users_groups:
            if x.name not in ldap_groups:
                try:
                    # g = Group.objects.get(name=x)
                    user_obj.groups.remove(x)
                    # user_obj.save()
                except Exception as e:
                    print(e)
        # add user to group if group exists in ldap and local group table
        for x in ldap_groups:
            if x not in [g.name for g in users_groups]:
                try:
                    g = Group.objects.get(name=x)
                    # g = Group.objects.get(name="tester")
                    user_obj.groups.add(g)
                    # user_obj.save()
                except Exception as e:
                    print(e)
        final_groups = user_obj.groups.all()
        final_groups = [x.name for x in final_groups]
        resp.data = {"groups": final_groups}
        return resp


@api_view(['GET', 'POST'])
def user_groups(request, format=None):
    try:
        name = request.META['REMOTE_USER']
    except KeyError:
        name = request.user.username

    # for testing, if username is '', set it to siteadmin
    if name == '':
        name = 'siteadmin'

    user_obj = User.objects.get(username=name)

    users_groups = user_obj.groups.all()
    if len(users_groups):
        return Response([x.name for x in users_groups])
    else:
        return Response(['anonymous'])


@api_view(['GET', 'POST'])
def dojo_login(request, format=None):
    try:
        user = request.META['REMOTE_USER']
        login(request, user, backend='django.contrib.auth.backends.RemoteUserBackend')
    except KeyError:
        user = request.user
    logger.log(0, user)
    return Response(user.username)
