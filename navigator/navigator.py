#!/usr/bin/env python3
import sys
import ssl
import signal
import asyncio
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
from typing import (
    Any,
)
from collections.abc import Callable
from aiohttp import web
import sockjs
import aiohttp_cors
from navconfig.logging import logging
from navigator.conf import (
    DEBUG,
    APP_NAME,
    APP_HOST,
    APP_PORT,
    EMAIL_CONTACT,
    Context,
    USE_SSL,
    SSL_CERT,
    SSL_KEY,
    CA_FILE,
    TEMPLATE_DIR
)
from navigator.functions import cPrint
from navigator.applications import (
    AppBase,
    AppHandler,
    app_startup
)
from navigator.exceptions import (
    NavException,
    ConfigError,
    InvalidArgument
)
# Exception Handlers
from navigator.exceptions.handlers import (
    nav_exception_handler,
    shutdown
)
from navigator.templating import TemplateParser
# websocket resources
from navigator.resources import WebSocket, channel_handler
from navigator.utils.functions import get_logger
from .apps import ApplicationInstaller


if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec
P = ParamSpec("P")


class Application(object):
    """Application.

        Main class for Navigator Application.
    Args:
        object (_type_): _description_
    """
    def __init__(
        self,
        *args: P.args,
        app: AppHandler = None,
        title: str = '',
        description: str = 'NAVIGATOR APP',
        contact: str = '',
        version: str = "0.0.1",
        enable_jinja_parser: bool = True,
        **kwargs: P.kwargs
    ) -> None:
        self.version = version
        self.use_ssl = USE_SSL
        self.description = description
        self.contact = contact
        if not contact:
            self.contact = EMAIL_CONTACT
        self.title = title if title else APP_NAME
        self.path = None
        self.host = APP_HOST
        self.port = APP_PORT
        self.debug = DEBUG
        # getting the application Logger
        self._logger = get_logger(self.title)
        if self.debug is False:
            # also, disable logging for 'aiohttp.access'
            aio = logging.getLogger('aiohttp.access')
            aio.setLevel(logging.CRITICAL)
        # template parser
        self.enable_jinja_parser = enable_jinja_parser
        # configuring asyncio loop
        try:
            self._loop = asyncio.new_event_loop()
        except RuntimeError:
            self._loop = asyncio.get_event_loop()
        self._loop.set_exception_handler(nav_exception_handler)
        asyncio.set_event_loop(self._loop)
        # May want to catch other signals too
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            self._loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(
                    shutdown(self._loop, s)
                )
            )
        if not app:
            # create an instance of AppHandler
            self.app = AppBase(Context, evt=self._loop, **kwargs)
        else:
            self.app = app(Context, evt=self._loop, **kwargs)
        # Sub-Application Startup:



    def get_app(self) -> web.Application:
        return self.app.App

    def __setitem__(self, k, v):
        self.app.App[k] = v

    def __getitem__(self, k):
        return self.app.App[k]

    def setup_app(self) -> web.Application:
        app = self.get_app()
        if self.enable_jinja_parser is True:
            try:
                parser = TemplateParser(
                    directory=TEMPLATE_DIR
                )
                app['template'] = parser
            except Exception as e:
                logging.exception(e)
                raise ConfigError(
                    f"Error on Template configuration, {e}"
                ) from e
        # setup The Application and Sub-Applications Startup
        installer = ApplicationInstaller()
        INSTALLED_APPS: list = installer.installed_apps()
        Context["INSTALLED_APPS"] = INSTALLED_APPS
        app_startup(INSTALLED_APPS, app, Context)
        # Configure Routes
        self.app.configure()
        cors = aiohttp_cors.setup(
            app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_methods="*",
                    allow_headers="*",
                    max_age=3600,
                )
            },
        )
        self.app.setup_cors(cors)
        self.app.setup_docs()
        return app

    def add_websockets(self) -> None:
        """
        add_websockets.
        description: enable support for websockets in the main App
        """
        app = self.get_app()
        if self.debug:
            logging.debug(":: Enabling WebSockets ::")
        # websockets
        app.router.add_route("GET", "/ws", WebSocket)
        # websocket channels
        app.router.add_route("GET", "/ws/{channel}", channel_handler)

    def add_routes(self, routes: list) -> None:
        """
        add_routes
        description: append a list of routes to routes dict
        """
        # TODO: avoid to add same route different times
        try:
            self.get_app().add_routes(routes)
        except Exception as ex:
            raise NavException(
                f"Error adding routes: {ex}"
            ) from ex

    def add_route(self, method: str = 'GET', route: str = None, fn: Callable = None) -> None:
        """add_route.

        Args:
            method (str, optional): http method. Defaults to 'GET'.
            route (str, optional): path. Defaults to None.
            fn (Callable, optional): function callable. Defaults to None.
        """
        self.get_app().router.add_route(method, route, fn)

    def add_static(self, route: str, path: str):
        """
        add_static
        description: register new route to static path.
        """
        self.get_app().add_static(route, path)

    def add_view(self, route: str, handler: Any):
        self.get_app().router.add_view(route, handler)

    def threaded_func(self, func: Callable, threaded: bool = False):
        @wraps(func)
        async def _wrap(request):
            result = None
            try:
                if threaded:

                    def blocking_function():
                        return asyncio.new_event_loop().run_until_complete(
                            func(request)
                        )

                    result = await self._loop.run_in_executor(
                        ThreadPoolExecutor(max_workers=1), blocking_function
                    )
                else:
                    result = await func(request)
                return result
            except (ValueError, RuntimeError) as err:
                self._logger.exception(err)
                raise InvalidArgument(
                    f"Error running Threaded Function: {err}"
                ) from err
        return _wrap

    def route(self, route: str, method: str = "GET", threaded: bool = False):
        """
        route.
        description: decorator for register a new HTTP route.
        """

        def _decorator(func):
            self.app.App.router.add_route(
                method, route, self.threaded_func(func, threaded)
            )
            return func

        return _decorator

    def add_get(self, route: str, threaded: bool = False) -> Callable:
        def _decorator(func):
            self.app.App.router.add_get(
                route, self.threaded_func(func, threaded), allow_head=False
            )
            return func

        return _decorator

    def Response(self, content: Any) -> web.Response:
        return web.Response(text=content)

    def get(self, route: str):
        def _decorator(func):
            self.app.App.router.add_get(route, func)

            @wraps(func)
            async def _wrap(request, *args, **kwargs):
                try:
                    return f"{func(request, args, **kwargs)}"
                except Exception as err:
                    self._logger.exception(err)
                    raise ConfigError(
                        f"Error configuring GET Route {route}: {err}"
                    ) from err
            return _wrap

        return _decorator

    @property
    def router(self):
        return self.app.App.router

    def post(self, route: str):
        def _decorator(func):
            self.app.App.router.add_post(route, func)

            @wraps(func)
            async def _wrap(request, *args, **kwargs):
                try:
                    return f"{func(request, args, **kwargs)}"
                except Exception as err:
                    self._logger.exception(err)
                    raise ConfigError(
                        f"Error configuring POST Route {route}: {err}"
                    ) from err

            return _wrap

        return _decorator

    def add_sock_endpoint(
        self, handler: Callable, name: str, route: str = "/sockjs/"
    ) -> None:
        app = self.get_app()
        sockjs.add_endpoint(app, handler, name=name, prefix=route)

    def setup(self):
        """setup.
        Get NAV application, used by Gunicorn.
        """
        # getting the resource App
        app = self.setup_app()
        return app

    def run(self):
        """run.
        Starting App.
        """
        # getting the resource App
        app = self.setup_app()
        if self.debug:
            cPrint(' :: Running in DEBUG mode :: ', level='DEBUG')
            logging.debug(' :: Running in DEBUG mode :: ')
        if self.use_ssl:
            if CA_FILE:
                ssl_context = ssl.create_default_context(
                    ssl.Purpose.SERVER_AUTH, cafile=CA_FILE
                )
            else:
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            ssl_context.load_cert_chain(SSL_CERT, SSL_KEY)
            try:
                web.run_app(
                    app, host=self.host, port=self.port, ssl_context=ssl_context
                )
            except Exception as err:
                logging.exception(err, stack_info=True)
                raise
        elif self.path:
            web.run_app(app, path=self.path, loop=self._loop)
        else:
            web.run_app(app, host=self.host, port=self.port, loop=self._loop)
