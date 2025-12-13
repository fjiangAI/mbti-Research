"""
自定义中间件：隔离admin和用户前端的session
"""
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.backends.base import UpdateError
from django.utils.cache import patch_vary_headers


class IsolatedSessionMiddleware(SessionMiddleware):
    """
    会话隔离中间件
    为admin和用户前端使用不同的session cookie名称，实现会话隔离
    
    Admin路径(/admin/)使用 'admin_sessionid' cookie
    用户前端使用默认的 SESSION_COOKIE_NAME cookie
    """
    
    # Admin使用的session cookie名称
    ADMIN_SESSION_COOKIE_NAME = 'admin_sessionid'
    
    def _get_session_cookie_name(self, request):
        """根据请求路径返回相应的session cookie名称"""
        if request.path.startswith('/admin/'):
            return self.ADMIN_SESSION_COOKIE_NAME
        return settings.SESSION_COOKIE_NAME
    
    def process_request(self, request):
        """处理请求，从相应的cookie中获取session"""
        cookie_name = self._get_session_cookie_name(request)
        session_key = request.COOKIES.get(cookie_name, None)
        request.session = self.SessionStore(session_key)
        
        # 保存cookie名称到request，供process_response使用
        request._session_cookie_name = cookie_name
    
    def process_response(self, request, response):
        """
        处理响应，设置正确的session cookie
        
        参考Django SessionMiddleware的实现，但使用不同的cookie名称来隔离admin和用户前端的session
        """
        try:
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response
        
        # 使用保存的cookie名称
        cookie_name = getattr(request, '_session_cookie_name', None)
        if cookie_name is None:
            cookie_name = self._get_session_cookie_name(request)
        
        # 先保存session（如果需要）
        if modified and not empty:
            try:
                request.session.save()
            except UpdateError:
                # Session过期，重新创建
                request.session.create()
        elif empty and cookie_name in request.COOKIES:
            # session为空但cookie存在，删除cookie
            response.delete_cookie(
                cookie_name,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
        
        # 如果需要保存session cookie
        if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
            # 准备cookie参数
            cookie_params = {
                'key': cookie_name,
                'value': request.session.session_key,
                'domain': settings.SESSION_COOKIE_DOMAIN,
                'path': settings.SESSION_COOKIE_PATH,
                'secure': settings.SESSION_COOKIE_SECURE,
                'httponly': settings.SESSION_COOKIE_HTTPONLY,
                'samesite': settings.SESSION_COOKIE_SAMESITE,
            }
            
            # 根据设置决定使用max_age还是expires（不能同时使用）
            if not request.session.get_expire_at_browser_close():
                # 使用max_age（推荐方式）
                cookie_params['max_age'] = request.session.get_expiry_age()
            
            # 设置cookie（使用自定义的cookie名称）
            response.set_cookie(**cookie_params)
        
        # 添加Vary头
        patch_vary_headers(response, ('Cookie',))
        
        return response

