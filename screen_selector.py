from __future__ import annotations

import ctypes
import io
import os
from ctypes import wintypes

from PIL import Image, ImageEnhance, ImageGrab, ImageWin


SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WM_CLOSE = 0x0010
WM_ERASEBKGND = 0x0014
WM_SETCURSOR = 0x0020
WM_KEYDOWN = 0x0100
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205

VK_ESCAPE = 0x1B
IDC_CROSS = 32515

WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080

SW_SHOW = 5
PS_SOLID = 0
NULL_BRUSH = 5
TRANSPARENT = 1

DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
PROCESS_PER_MONITOR_DPI_AWARE = 2

SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000
DIB_RGB_COLORS = 0
BI_RGB = 0
RGN_ERROR = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class RGBQUAD(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", ctypes.c_ubyte),
        ("rgbGreen", ctypes.c_ubyte),
        ("rgbRed", ctypes.c_ubyte),
        ("rgbReserved", ctypes.c_ubyte),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", RGBQUAD * 1),
    ]


def normalizar_region(
    inicio: tuple[int, int],
    final: tuple[int, int],
    ancho: int,
    alto: int,
) -> tuple[int, int, int, int] | None:
    """Return a clamped left/top/right/bottom selection or None if tiny."""
    x1, y1 = inicio
    x2, y2 = final
    izquierda = max(0, min(int(x1), int(x2)))
    arriba = max(0, min(int(y1), int(y2)))
    derecha = min(int(ancho), max(int(x1), int(x2)))
    abajo = min(int(alto), max(int(y1), int(y2)))

    if derecha - izquierda < 12 or abajo - arriba < 12:
        return None

    return izquierda, arriba, derecha, abajo


def _imagen_a_jpeg(imagen: Image.Image) -> bytes:
    if imagen.mode != "RGB":
        imagen = imagen.convert("RGB")

    with io.BytesIO() as buffer:
        imagen.save(buffer, format="JPEG", quality=88, optimize=True)
        return buffer.getvalue()


def _preparar_dpi() -> None:
    if os.name != "nt":
        return

    user32 = ctypes.windll.user32

    try:
        # The selector runs in an asyncio worker after Flet has already created
        # its window. Process DPI awareness can no longer be changed at that
        # point, but the selector thread can still use Per-Monitor V2.
        establecer_hilo = user32.SetThreadDpiAwarenessContext
        establecer_hilo.argtypes = [wintypes.HANDLE]
        establecer_hilo.restype = wintypes.HANDLE
        contexto_anterior = establecer_hilo(
            ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        )

        if contexto_anterior:
            return
    except Exception:
        pass

    try:
        establecer_proceso = user32.SetProcessDpiAwarenessContext
        establecer_proceso.argtypes = [wintypes.HANDLE]
        establecer_proceso.restype = wintypes.BOOL

        if establecer_proceso(
            ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        ):
            return
    except Exception:
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(
            PROCESS_PER_MONITOR_DPI_AWARE
        )
    except Exception:
        pass


def _capturar_escritorio_virtual(
    izquierda: int,
    arriba: int,
    ancho: int,
    alto: int,
) -> Image.Image:
    """Capture the exact Win32 virtual desktop without Pillow DPI scaling."""
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    user32.GetDC.restype = wintypes.HDC
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]

    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleBitmap.restype = wintypes.HANDLE
    gdi32.CreateCompatibleBitmap.argtypes = [
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
    ]
    gdi32.SelectObject.restype = wintypes.HANDLE
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    gdi32.BitBlt.restype = wintypes.BOOL
    gdi32.BitBlt.argtypes = [
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.DWORD,
    ]
    gdi32.GetDIBits.restype = ctypes.c_int
    gdi32.GetDIBits.argtypes = [
        wintypes.HDC,
        wintypes.HANDLE,
        wintypes.UINT,
        wintypes.UINT,
        wintypes.LPVOID,
        ctypes.POINTER(BITMAPINFO),
        wintypes.UINT,
    ]
    gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]

    dc_pantalla = user32.GetDC(None)
    if not dc_pantalla:
        raise ctypes.WinError()

    dc_memoria = None
    bitmap = None
    bitmap_anterior = None
    bitmap_seleccionado = False

    try:
        dc_memoria = gdi32.CreateCompatibleDC(dc_pantalla)
        if not dc_memoria:
            raise ctypes.WinError()

        bitmap = gdi32.CreateCompatibleBitmap(dc_pantalla, ancho, alto)
        if not bitmap:
            raise ctypes.WinError()

        bitmap_anterior = gdi32.SelectObject(dc_memoria, bitmap)
        if not bitmap_anterior:
            raise ctypes.WinError()
        bitmap_seleccionado = True

        if not gdi32.BitBlt(
            dc_memoria,
            0,
            0,
            ancho,
            alto,
            dc_pantalla,
            izquierda,
            arriba,
            SRCCOPY | CAPTUREBLT,
        ):
            raise ctypes.WinError()

        # GetDIBits requires the bitmap not to be selected into a DC.
        if not gdi32.SelectObject(dc_memoria, bitmap_anterior):
            raise ctypes.WinError()
        bitmap_seleccionado = False

        informacion = BITMAPINFO()
        informacion.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        informacion.bmiHeader.biWidth = ancho
        # A negative height makes GDI return rows from top to bottom.
        informacion.bmiHeader.biHeight = -alto
        informacion.bmiHeader.biPlanes = 1
        informacion.bmiHeader.biBitCount = 32
        informacion.bmiHeader.biCompression = BI_RGB

        datos = ctypes.create_string_buffer(ancho * alto * 4)
        filas = gdi32.GetDIBits(
            dc_pantalla,
            bitmap,
            0,
            alto,
            datos,
            ctypes.byref(informacion),
            DIB_RGB_COLORS,
        )

        if filas != alto:
            raise ctypes.WinError()

        return Image.frombytes(
            "RGB",
            (ancho, alto),
            datos.raw,
            "raw",
            "BGRX",
            ancho * 4,
            1,
        )
    finally:
        if dc_memoria and bitmap_anterior and bitmap_seleccionado:
            gdi32.SelectObject(dc_memoria, bitmap_anterior)
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if dc_memoria:
            gdi32.DeleteDC(dc_memoria)
        user32.ReleaseDC(None, dc_pantalla)


def _dibujar_region_original_sin_escalar(
    dc: int,
    dib_original: ImageWin.Dib,
    gdi32,
    seleccion: tuple[int, int, int, int],
    ancho_virtual: int,
    alto_virtual: int,
) -> None:
    """Reveal the selected area by clipping a single full-size desktop draw."""
    estado_dc = gdi32.SaveDC(dc)
    if not estado_dc:
        return

    try:
        izq, sup, der, inf = seleccion
        if gdi32.IntersectClipRect(dc, izq, sup, der, inf) == RGN_ERROR:
            return

        # Drawing the entire DIB into the same-size desktop rectangle avoids
        # ImageWin stretching a source sub-rectangle on scaled Windows screens.
        dib_original.draw(dc, (0, 0, ancho_virtual, alto_virtual))
    finally:
        gdi32.RestoreDC(dc, estado_dc)


def seleccionar_region_pantalla_jpeg(
    instruccion: str,
    cancelar: str,
) -> bytes | None:
    """Display a native Windows selector and return only the chosen region."""
    _preparar_dpi()

    if os.name != "nt":
        captura = ImageGrab.grab(all_screens=True)
        return _imagen_a_jpeg(captura)

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    gdi32 = ctypes.windll.gdi32

    izquierda_virtual = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    arriba_virtual = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    ancho_virtual = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    alto_virtual = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))

    if ancho_virtual <= 0 or alto_virtual <= 0:
        raise RuntimeError("Windows returned an invalid virtual-screen size.")

    captura = _capturar_escritorio_virtual(
        izquierda_virtual,
        arriba_virtual,
        ancho_virtual,
        alto_virtual,
    )

    if captura.size != (ancho_virtual, alto_virtual):
        raise RuntimeError(
            "The Windows desktop capture does not match the selector size."
        )

    oscura = ImageEnhance.Brightness(captura.convert("RGB")).enhance(0.32)
    dib_oscura = ImageWin.Dib(oscura)
    dib_original = ImageWin.Dib(captura.convert("RGB"))

    seleccion: tuple[int, int, int, int] | None = None
    inicio: tuple[int, int] | None = None
    arrastrando = False
    cancelado = False

    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(
        LRESULT,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ("style", wintypes.UINT),
            ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", wintypes.HICON),
            ("hCursor", wintypes.HANDLE),
            ("hbrBackground", wintypes.HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
        ]

    class PAINTSTRUCT(ctypes.Structure):
        _fields_ = [
            ("hdc", wintypes.HDC),
            ("fErase", wintypes.BOOL),
            ("rcPaint", wintypes.RECT),
            ("fRestore", wintypes.BOOL),
            ("fIncUpdate", wintypes.BOOL),
            ("rgbReserved", ctypes.c_byte * 32),
        ]

    user32.DefWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        wintypes.HMENU,
        wintypes.HINSTANCE,
        wintypes.LPVOID,
    ]
    user32.BeginPaint.restype = wintypes.HDC
    user32.BeginPaint.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(PAINTSTRUCT),
    ]
    user32.EndPaint.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(PAINTSTRUCT),
    ]
    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    user32.LoadCursorW.restype = wintypes.HANDLE
    user32.SetCursor.restype = wintypes.HANDLE
    user32.SetCursor.argtypes = [wintypes.HANDLE]
    user32.SetCapture.restype = wintypes.HWND
    user32.SetCapture.argtypes = [wintypes.HWND]
    user32.InvalidateRect.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.RECT),
        wintypes.BOOL,
    ]
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetFocus.restype = wintypes.HWND
    user32.SetFocus.argtypes = [wintypes.HWND]
    user32.UpdateWindow.argtypes = [wintypes.HWND]
    user32.DrawTextW.argtypes = [
        wintypes.HDC,
        wintypes.LPCWSTR,
        ctypes.c_int,
        ctypes.POINTER(wintypes.RECT),
        wintypes.UINT,
    ]
    user32.GetMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG),
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
    ]
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.restype = LRESULT
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.UnregisterClassW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.HINSTANCE,
    ]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    gdi32.CreatePen.restype = wintypes.HANDLE
    gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.COLORREF]
    gdi32.SelectObject.restype = wintypes.HANDLE
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    gdi32.GetStockObject.restype = wintypes.HANDLE
    gdi32.GetStockObject.argtypes = [ctypes.c_int]
    gdi32.Rectangle.argtypes = [
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
    ]
    gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
    gdi32.SaveDC.restype = ctypes.c_int
    gdi32.SaveDC.argtypes = [wintypes.HDC]
    gdi32.RestoreDC.restype = wintypes.BOOL
    gdi32.RestoreDC.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.IntersectClipRect.restype = ctypes.c_int
    gdi32.IntersectClipRect.argtypes = [
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
    ]

    cursor_cruz = user32.LoadCursorW(None, ctypes.c_void_p(IDC_CROSS))

    def coordenadas(lparam: int) -> tuple[int, int]:
        x = ctypes.c_short(lparam & 0xFFFF).value
        y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
        return int(x), int(y)

    def colorref(rojo: int, verde: int, azul: int) -> int:
        return rojo | (verde << 8) | (azul << 16)

    @WNDPROC
    def procedimiento(
        hwnd: int,
        mensaje: int,
        wparam: int,
        lparam: int,
    ) -> int:
        nonlocal seleccion, inicio, arrastrando, cancelado

        if mensaje == WM_ERASEBKGND:
            return 1

        if mensaje == WM_SETCURSOR:
            user32.SetCursor(cursor_cruz)
            return 1

        if mensaje == WM_LBUTTONDOWN:
            inicio = coordenadas(lparam)
            seleccion = None
            arrastrando = True
            user32.SetCapture(hwnd)
            return 0

        if mensaje == WM_MOUSEMOVE and arrastrando and inicio is not None:
            seleccion = normalizar_region(
                inicio,
                coordenadas(lparam),
                ancho_virtual,
                alto_virtual,
            )
            user32.InvalidateRect(hwnd, None, False)
            return 0

        if mensaje == WM_LBUTTONUP and arrastrando:
            arrastrando = False
            user32.ReleaseCapture()
            if inicio is not None:
                seleccion = normalizar_region(
                    inicio,
                    coordenadas(lparam),
                    ancho_virtual,
                    alto_virtual,
                )
            if seleccion is not None:
                user32.DestroyWindow(hwnd)
            else:
                user32.InvalidateRect(hwnd, None, False)
            return 0

        if (
            mensaje in {WM_RBUTTONUP, WM_CLOSE}
            or (mensaje == WM_KEYDOWN and wparam == VK_ESCAPE)
        ):
            cancelado = True
            seleccion = None
            user32.DestroyWindow(hwnd)
            return 0

        if mensaje == WM_PAINT:
            pintura = PAINTSTRUCT()
            dc = user32.BeginPaint(hwnd, ctypes.byref(pintura))
            try:
                dib_oscura.draw(dc, (0, 0, ancho_virtual, alto_virtual))

                if seleccion is not None:
                    izq, sup, der, inf = seleccion
                    _dibujar_region_original_sin_escalar(
                        dc,
                        dib_original,
                        gdi32,
                        seleccion,
                        ancho_virtual,
                        alto_virtual,
                    )

                    lapiz = gdi32.CreatePen(
                        PS_SOLID,
                        3,
                        colorref(168, 111, 75),
                    )
                    lapiz_anterior = gdi32.SelectObject(dc, lapiz)
                    pincel_anterior = gdi32.SelectObject(
                        dc,
                        gdi32.GetStockObject(NULL_BRUSH),
                    )
                    gdi32.Rectangle(dc, izq, sup, der, inf)
                    gdi32.SelectObject(dc, pincel_anterior)
                    gdi32.SelectObject(dc, lapiz_anterior)
                    gdi32.DeleteObject(lapiz)

                gdi32.SetBkMode(dc, TRANSPARENT)
                gdi32.SetTextColor(dc, colorref(255, 244, 232))
                user32.DrawTextW(
                    dc,
                    instruccion,
                    -1,
                    ctypes.byref(wintypes.RECT(24, 22, ancho_virtual - 24, 58)),
                    0,
                )
                gdi32.SetTextColor(dc, colorref(232, 201, 178))
                user32.DrawTextW(
                    dc,
                    cancelar,
                    -1,
                    ctypes.byref(wintypes.RECT(24, 54, ancho_virtual - 24, 88)),
                    0,
                )
            finally:
                user32.EndPaint(hwnd, ctypes.byref(pintura))
            return 0

        if mensaje == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0

        return int(user32.DefWindowProcW(hwnd, mensaje, wparam, lparam))

    instancia = kernel32.GetModuleHandleW(None)
    nombre_clase = f"NovaLensScreenSelector_{os.getpid()}"
    clase = WNDCLASSW(
        style=0,
        lpfnWndProc=procedimiento,
        cbClsExtra=0,
        cbWndExtra=0,
        hInstance=instancia,
        hIcon=None,
        hCursor=cursor_cruz,
        hbrBackground=None,
        lpszMenuName=None,
        lpszClassName=nombre_clase,
    )

    if not user32.RegisterClassW(ctypes.byref(clase)):
        raise ctypes.WinError()

    hwnd = user32.CreateWindowExW(
        WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
        nombre_clase,
        "Nova Lens Screen Region",
        WS_POPUP | WS_VISIBLE,
        izquierda_virtual,
        arriba_virtual,
        ancho_virtual,
        alto_virtual,
        None,
        None,
        instancia,
        None,
    )

    if not hwnd:
        user32.UnregisterClassW(nombre_clase, instancia)
        raise ctypes.WinError()

    user32.ShowWindow(hwnd, SW_SHOW)
    user32.SetForegroundWindow(hwnd)
    user32.SetFocus(hwnd)
    user32.UpdateWindow(hwnd)

    mensaje = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(mensaje), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(mensaje))
            user32.DispatchMessageW(ctypes.byref(mensaje))
    finally:
        user32.UnregisterClassW(nombre_clase, instancia)

    if cancelado or seleccion is None:
        return None

    return _imagen_a_jpeg(captura.crop(seleccion))
