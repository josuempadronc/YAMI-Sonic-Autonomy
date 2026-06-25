"""
YAMI: SONIC AUTONOMY  v2.0
Reproductor arcano con orbe animado, reconocimiento de voz y UI grimorio.
Arquitectura: Kivy + SoundLoader + Pyjnius (Android)
"""
import os
import math
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import (
    Color, Ellipse, Line, Rectangle,
    RoundedRectangle, PushMatrix, PopMatrix, Rotate
)
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import NumericProperty, BooleanProperty
from kivy.animation import Animation

# ── Android ──────────────────────────────────────────────────────────────────
try:
    from jnius import autoclass, PythonJavaClass, java_method
    ANDROID = True
except ImportError:
    ANDROID = False

# ── Runas éldar para decoración ───────────────────────────────────────────────
RUNAS = 'ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜᛞᛟ'


# ─────────────────────────────────────────────────────────────────────────────
# ORBE ANIMADO
# ─────────────────────────────────────────────────────────────────────────────
class OrbWidget(Widget):
    """
    Orbe arcano con:
    - Anillos concéntricos (dorado + morado)
    - Núcleo pulsante con gradiente
    - Runas giratorias en anillo exterior
    - Rayos de energía eléctrica
    - Partículas flotantes
    """
    angle       = NumericProperty(0)     # rotación anillo runas
    angle2      = NumericProperty(0)     # rotación anillo interior (inverso)
    pulse       = NumericProperty(0)     # 0→1 pulso del núcleo
    ray_phase   = NumericProperty(0)     # fase de los rayos
    is_playing  = BooleanProperty(False)

    # Posiciones de partículas (ángulo, radio, tamaño)
    _particles = [(i * 37.3, 68 + (i % 4) * 8, 2 + (i % 3)) for i in range(12)]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pulse_dir = 1
        self.bind(pos=self._redraw, size=self._redraw,
                  angle=self._redraw, angle2=self._redraw,
                  pulse=self._redraw, ray_phase=self._redraw,
                  is_playing=self._redraw)
        Clock.schedule_interval(self._tick, 1 / 20)

    def _tick(self, dt):
        speed = 1.8 if self.is_playing else 0.6
        self.angle  = (self.angle  + dt * 28 * speed) % 360
        self.angle2 = (self.angle2 - dt * 18 * speed) % 360
        self.ray_phase = (self.ray_phase + dt * 2.2) % (2 * math.pi)
        # Pulso suave
        self.pulse += dt * self._pulse_dir * (0.9 if self.is_playing else 0.35)
        if self.pulse >= 1:
            self.pulse = 1; self._pulse_dir = -1
        elif self.pulse <= 0:
            self.pulse = 0; self._pulse_dir = 1

    def _redraw(self, *args):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        p = self.pulse

        with self.canvas:
            # ── Halo exterior difuso
            Color(0.45, 0, 0.8, 0.06 + p * 0.06)
            d_halo = 160 + p * 12
            Ellipse(pos=(cx - d_halo/2, cy - d_halo/2), size=(d_halo, d_halo))

            # ── Anillo de RUNAS (giratorio externo)
            self._draw_rune_ring(cx, cy, radius=64, n=12, angle_offset=self.angle)

            # ── Anillo dorado exterior
            Color(0.72, 0.50, 0, 0.55 + p * 0.25)
            Line(ellipse=(cx-58, cy-58, 116, 116), width=1.3)

            # ── Anillo morado medio (contra-rotatorio)
            self._draw_rune_ring(cx, cy, radius=46, n=8, angle_offset=self.angle2,
                                 color=(0.6, 0.1, 1, 0.5 + p*0.3))
            Color(0.5, 0, 0.9, 0.6 + p * 0.2)
            Line(ellipse=(cx-44, cy-44, 88, 88), width=1.5)

            # ── RAYOS de energía (4 + 4 diagonales)
            self._draw_rays(cx, cy, p)

            # ── Núcleo (relleno morado pulsante)
            r_core = 30 + p * 5
            Color(0.28, 0, 0.55, 0.9)
            Ellipse(pos=(cx-r_core, cy-r_core), size=(r_core*2, r_core*2))

            # Brillo interior (capa 1)
            r_glow1 = 20 + p * 4
            Color(0.55, 0.1, 0.9, 0.75)
            Ellipse(pos=(cx-r_glow1, cy-r_glow1), size=(r_glow1*2, r_glow1*2))

            # Brillo interior (capa 2)
            r_glow2 = 10 + p * 3
            Color(0.78, 0.45, 1, 0.9)
            Ellipse(pos=(cx-r_glow2, cy-r_glow2), size=(r_glow2*2, r_glow2*2))

            # Punto central blanco
            Color(1, 0.95, 1, 0.95)
            Ellipse(pos=(cx-5, cy-5), size=(10, 10))

            # ── Anillo interior morado
            Color(0.65, 0.15, 1, 0.4 + p * 0.4)
            Line(ellipse=(cx-r_core, cy-r_core, r_core*2, r_core*2), width=1.2)

            # ── Partículas flotantes
            self._draw_particles(cx, cy)

    def _draw_rune_ring(self, cx, cy, radius, n, angle_offset,
                        color=(0.72, 0.50, 0, 0.45)):
        """Dibuja N runas en círculo, rotando con angle_offset."""
        Color(*color)
        for i in range(n):
            a = math.radians(angle_offset + i * (360 / n))
            rx = cx + radius * math.cos(a)
            ry = cy + radius * math.sin(a)
            # Línea corta representando una runa
            Line(
                points=[
                    rx - 3 * math.sin(a), ry + 3 * math.cos(a),
                    rx + 3 * math.sin(a), ry - 3 * math.cos(a)
                ],
                width=1.1
            )
            Line(
                points=[rx - 3, ry, rx + 3, ry],
                width=0.8
            )

    def _draw_rays(self, cx, cy, p):
        """Rayos de energía eléctrica animados."""
        ray_data = [
            (90,  55, 80),
            (270, 55, 80),
            (0,   55, 80),
            (180, 55, 80),
            (45,  50, 70),
            (135, 50, 70),
            (225, 50, 70),
            (315, 50, 70),
        ]
        for i, (base_angle, r_start, r_end) in enumerate(ray_data):
            phase_offset = i * 0.78
            intensity = abs(math.sin(self.ray_phase + phase_offset))
            if intensity < 0.2:
                continue
            alpha = intensity * (0.5 + p * 0.4)
            wobble = math.sin(self.ray_phase * 2.3 + phase_offset) * 6
            a = math.radians(base_angle + wobble)
            x1 = cx + r_start * math.cos(a)
            y1 = cy + r_start * math.sin(a)
            x2 = cx + (r_end + p * 10) * math.cos(a)
            y2 = cy + (r_end + p * 10) * math.sin(a)
            # Rayo principal morado
            Color(0.6, 0.1, 1, alpha * 0.85)
            Line(points=[x1, y1, x2, y2], width=1.4)
            # Rayo secundario dorado (más corto)
            mid = 0.55
            Color(0.85, 0.65, 0, alpha * 0.5)
            Line(points=[
                x1 + (x2-x1)*mid, y1 + (y2-y1)*mid,
                x2, y2
            ], width=0.8)

    def _draw_particles(self, cx, cy):
        """Partículas pequeñas flotando alrededor del orbe."""
        t = self.ray_phase
        for i, (base_angle, base_r, size) in enumerate(self._particles):
            a = math.radians(base_angle + self.angle * 0.4 + i * 5)
            drift = math.sin(t * 0.8 + i * 1.1) * 8
            r = base_r + drift
            px = cx + r * math.cos(a)
            py = cy + r * math.sin(a)
            alpha = 0.3 + 0.5 * abs(math.sin(t * 0.6 + i * 0.9))
            if i % 3 == 0:
                Color(0.85, 0.65, 0, alpha)
            else:
                Color(0.6, 0.1, 1, alpha * 0.7)
            Ellipse(pos=(px - size/2, py - size/2), size=(size, size))


# ─────────────────────────────────────────────────────────────────────────────
# BARRA DE PROGRESO CUSTOM
# ─────────────────────────────────────────────────────────────────────────────
class ProgressWidget(Widget):
    progress = NumericProperty(0.0)  # 0.0 → 1.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw, progress=self._redraw)

    def _redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Track
            Color(0.28, 0, 0.5, 0.45)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[3])
            Color(0.45, 0, 0.75, 0.32)
            Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 3], width=0.8)
            # Fill
            fill_w = max(self.progress * self.width, 0)
            if fill_w > 0:
                Color(0.72, 0.50, 0, 0.92)
                RoundedRectangle(
                    pos=self.pos,
                    size=(fill_w, self.height),
                    radius=[3]
                )
                # Punto de progreso
                Color(1, 0.9, 0.4, 1)
                dot = 8
                Ellipse(
                    pos=(self.x + fill_w - dot/2, self.center_y - dot/2),
                    size=(dot, dot)
                )

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.progress = (touch.x - self.x) / self.width
            App.get_running_app().seek(self.progress)
            return True


# ─────────────────────────────────────────────────────────────────────────────
# ÍTEM DE CANCIÓN
# ─────────────────────────────────────────────────────────────────────────────
class SongItem(Button):
    def __init__(self, nombre, indice, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.nombre = nombre
        self.indice = indice
        self.app_ref = app_ref
        self.text = f'  ᚱ  {nombre}'
        self.font_size = '11sp'
        self.halign = 'left'
        self.size_hint_y = None
        self.height = '36dp'
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (0.82, 0.82, 0.82, 1)
        self.bold = False
        self.bind(on_press=lambda i: self.app_ref.reproducir_indice(self.indice))
        self.bind(pos=self._upd, size=self._upd)
        self._activo = False
        with self.canvas.before:
            self._c_bg  = Color(0.35, 0, 0.6, 0.09)
            self._r_bg  = RoundedRectangle(pos=self.pos, size=self.size, radius=[3])
            self._c_brd = Color(0.45, 0, 0.75, 0.22)
            self._l_brd = Line(rounded_rectangle=[self.x, self.y, self.width, self.height, 3], width=0.7)

    def _upd(self, *_):
        self._r_bg.pos  = self.pos
        self._r_bg.size = self.size
        self._l_brd.rounded_rectangle = [self.x, self.y, self.width, self.height, 3]

    def set_activo(self, v):
        self._activo = v
        if v:
            self._c_bg.rgba  = (0.45, 0, 0.82, 0.32)
            self._c_brd.rgba = (0.80, 0.58, 0, 0.92)
            self.color = (0.88, 0.65, 0, 1)
            self.bold  = True
            self.text  = f'  ▶  {self.nombre}'
        else:
            self._c_bg.rgba  = (0.35, 0, 0.6, 0.09)
            self._c_brd.rgba = (0.45, 0, 0.75, 0.22)
            self.color = (0.82, 0.82, 0.82, 1)
            self.bold  = False
            self.text  = f'  ᚱ  {self.nombre}'


# ─────────────────────────────────────────────────────────────────────────────
# RECONOCIMIENTO DE VOZ (Android Pyjnius)
# ─────────────────────────────────────────────────────────────────────────────
if ANDROID:
    class YAMIVoiceListener(PythonJavaClass):
        """Implementa android.speech.RecognitionListener via Pyjnius."""
        __javainterfaces__ = ['android/speech/RecognitionListener']
        __javacontext__ = 'app'

        def __init__(self, app_ref):
            super().__init__()
            self.app_ref = app_ref

        @java_method('(Landroid/os/Bundle;)V')
        def onReadyForSpeech(self, params):
            Clock.schedule_once(lambda dt:
                self.app_ref._set_mic_ui(True, 'ESCUCHANDO...'), 0)

        @java_method('(Landroid/os/Bundle;)V')
        def onResults(self, results):
            SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
            matches = results.getStringArrayList(
                SpeechRecognizer.RESULTS_RECOGNITION
            )
            if matches and matches.size() > 0:
                texto = matches.get(0)
                Clock.schedule_once(
                    lambda dt, t=texto: self.app_ref.procesar_comando_voz(t), 0
                )

        @java_method('(I)V')
        def onError(self, error):
            Clock.schedule_once(lambda dt:
                self.app_ref._on_voice_error(error), 0)

        # Firmas exactas del interface RecognitionListener de Android
        @java_method('()V')
        def onBeginningOfSpeech(self): pass

        @java_method('()V')
        def onEndOfSpeech(self): pass

        @java_method('(F)V')
        def onRmsChanged(self, rmsdB): pass

        @java_method('([B)V')
        def onBufferReceived(self, buffer): pass

        @java_method('(Landroid/os/Bundle;)V')
        def onPartialResults(self, partialResults): pass

        @java_method('(ILandroid/os/Bundle;)V')
        def onEvent(self, eventType, params): pass

    class _Runnable(PythonJavaClass):
        """Wrapper para ejecutar código Python en el UI thread de Android."""
        __javainterfaces__ = ['java/lang/Runnable']
        __javacontext__ = 'app'

        def __init__(self, fn):
            super().__init__()
            self._fn = fn

        @java_method('()V')
        def run(self):
            self._fn()


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT RAÍZ
# ─────────────────────────────────────────────────────────────────────────────
class YAMI_Layout(BoxLayout):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# APP PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
class YAMI_Sonic_Autonomy(App):

    def build(self):
        Window.clearcolor = (0.03, 0.01, 0.07, 1)
        Builder.load_file('yami.kv')

        # Estado
        self.carpeta_musica = "/storage/emulated/0/Music"
        self.sonido_actual  = None
        self.lista_musica   = []
        self.indice_actual  = 0
        self.en_pausa       = False
        self.song_items     = []
        self.mic_activo     = False
        self._recognizer    = None

        self.root_widget = YAMI_Layout()

        # Ticks
        Clock.schedule_interval(self._tick_progreso, 0.5)

        if ANDROID:
            # Pedir permisos primero; la biblioteca carga en el callback
            Clock.schedule_once(self._pedir_permisos, 0.6)
        else:
            # En PC cargar directo
            Clock.schedule_once(self.cargar_biblioteca, 0.8)

        return self.root_widget

    # ── BIBLIOTECA ──────────────────────────────────────────────────────────

    def cargar_biblioteca(self, dt=0):
        self._set_status('ESCANEANDO...')
        threading.Thread(target=self._escanear_bg, daemon=True).start()

    def _escanear_bg(self):
        """Escanea archivos en background para no bloquear la UI."""
        if ANDROID:
            archivos = self._escanear_musica_android()
        elif os.path.exists(self.carpeta_musica):
            archivos = sorted([
                os.path.join(self.carpeta_musica, f)
                for f in os.listdir(self.carpeta_musica)
                if f.lower().endswith(('.mp3', '.ogg', '.wav', '.flac', '.m4a'))
            ])
        else:
            archivos = []
        Clock.schedule_once(lambda dt, a=archivos: self._poblar_biblioteca(a), 0)

    def _poblar_biblioteca(self, archivos):
        """Actualiza la UI con los archivos encontrados (main thread)."""
        grid = self.root_widget.ids.lista_grid
        grid.clear_widgets()
        self.song_items.clear()

        self.lista_musica = archivos if archivos else [
            "Despertar del Grimorium.mp3",
            "Runas de Fuego.mp3",
            "Tormenta Arcana.mp3",
            "El Último Hechizo.mp3",
            "Autonomía Absoluta.mp3",
            "Ecos del Vacío.mp3",
            "Resonancia de Mando.mp3",
        ]

        self.root_widget.ids.lbl_biblioteca.text = f'BIBLIOTECA: {len(self.lista_musica)} TEMAS'

        for i, ruta in enumerate(self.lista_musica):
            display = os.path.basename(ruta)
            item = SongItem(nombre=display, indice=i, app_ref=self)
            grid.add_widget(item)
            self.song_items.append(item)

        if self.lista_musica:
            self._actualizar_ui_cancion()
            self._set_status('NÚCLEO LISTO')

    def _escanear_musica_android(self):
        """Escanea Music, Download y subdirectorios buscando audio."""
        ext = ('.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac', '.opus')
        carpetas = [
            "/storage/emulated/0/Music",
            "/storage/emulated/0/music",
            "/storage/emulated/0/Download",
            "/storage/emulated/0/Downloads",
            "/sdcard/Music",
            "/sdcard/Download",
        ]
        archivos = []
        seen = set()
        for carpeta in carpetas:
            if not os.path.exists(carpeta):
                continue
            try:
                for entry in os.listdir(carpeta):
                    ruta = os.path.join(carpeta, entry)
                    if entry.lower().endswith(ext):
                        key = os.path.realpath(ruta)
                        if key not in seen:
                            seen.add(key)
                            archivos.append(ruta)
                    elif os.path.isdir(ruta):
                        try:
                            for sub in os.listdir(ruta):
                                if sub.lower().endswith(ext):
                                    sp = os.path.join(ruta, sub)
                                    key = os.path.realpath(sp)
                                    if key not in seen:
                                        seen.add(key)
                                        archivos.append(sp)
                        except Exception:
                            pass
            except Exception:
                pass
        return sorted(archivos, key=lambda x: os.path.basename(x).lower())

    def _actualizar_ui_cancion(self):
        nombre = self.lista_musica[self.indice_actual]
        display = os.path.basename(nombre).rsplit('.', 1)[0]
        self.root_widget.ids.lbl_cancion.text = display
        for i, item in enumerate(self.song_items):
            item.set_activo(i == self.indice_actual)

    # ── CONTROLES ───────────────────────────────────────────────────────────

    def reproducir(self):
        if not self.lista_musica:
            self._set_status('BIBLIOTECA VACÍA')
            return
        if self.en_pausa and self.sonido_actual:
            self.sonido_actual.play()
            self.en_pausa = False
            self._set_status('▶ REPRODUCIENDO')
            self.root_widget.ids.orb.is_playing = True
            return
        self._cargar_y_play()

    def reproducir_indice(self, indice):
        self.indice_actual = indice
        self.en_pausa = False
        if self.sonido_actual:
            self.sonido_actual.stop()
            self.sonido_actual = None
        self._cargar_y_play()

    def _cargar_y_play(self):
        if self.sonido_actual:
            self.sonido_actual.stop()
            self.sonido_actual = None

        ruta = self.lista_musica[self.indice_actual]
        if not os.path.isabs(ruta):
            ruta = os.path.join(self.carpeta_musica, ruta)

        if not os.path.exists(ruta):
            self._set_status('▶ MODO DEMO')
            self._actualizar_ui_cancion()
            self.root_widget.ids.orb.is_playing = True
            return

        self._set_status('CARGANDO...')
        threading.Thread(target=self._cargar_audio_bg, args=(ruta,), daemon=True).start()

    def _cargar_audio_bg(self, ruta):
        """Carga el audio en background para no bloquear la UI."""
        sonido = SoundLoader.load(ruta)
        Clock.schedule_once(lambda dt, s=sonido: self._iniciar_play(s), 0)

    def _iniciar_play(self, sonido):
        """Inicia la reproducción en el main thread."""
        if sonido:
            self.sonido_actual = sonido
            self.sonido_actual.volume = self.root_widget.ids.vol_slider.value
            self.sonido_actual.bind(on_stop=self._on_fin)
            self.sonido_actual.play()
            self.en_pausa = False
            self._set_status('▶ REPRODUCIENDO')
            self._actualizar_ui_cancion()
            self.root_widget.ids.orb.is_playing = True
        else:
            self._set_status('ERROR: FORMATO NO SOPORTADO')

    def pausar(self):
        if self.sonido_actual and self.sonido_actual.state == 'play':
            self.sonido_actual.stop()
            self.en_pausa = True
            self._set_status('⏸ EN PAUSA')
            self.root_widget.ids.orb.is_playing = False

    def detener(self):
        if self.sonido_actual:
            self.sonido_actual.stop()
            self.sonido_actual = None
        self.en_pausa = False
        self.root_widget.ids.prog_widget.progress = 0
        self.root_widget.ids.lbl_tiempo.text = '0:00'
        self._set_status('⏹ DETENIDO')
        self.root_widget.ids.orb.is_playing = False

    def siguiente(self):
        if not self.lista_musica:
            return
        self.indice_actual = (self.indice_actual + 1) % len(self.lista_musica)
        self.en_pausa = False
        if self.sonido_actual:
            self.sonido_actual.stop()
            self.sonido_actual = None
        self._cargar_y_play()

    def anterior(self):
        if not self.lista_musica:
            return
        self.indice_actual = (self.indice_actual - 1) % len(self.lista_musica)
        self.en_pausa = False
        if self.sonido_actual:
            self.sonido_actual.stop()
            self.sonido_actual = None
        self._cargar_y_play()

    def cambiar_volumen(self, instance, value):
        if self.sonido_actual:
            self.sonido_actual.volume = value

    def seek(self, ratio):
        """Saltar a posición en la canción (0.0–1.0)."""
        if self.sonido_actual and self.sonido_actual.length:
            self.sonido_actual.seek(ratio * self.sonido_actual.length)

    def _on_fin(self, *args):
        Clock.schedule_once(lambda dt: self.siguiente(), 0.4)

    # ── PROGRESO ────────────────────────────────────────────────────────────

    def _tick_progreso(self, dt):
        if not self.sonido_actual:
            return
        if self.sonido_actual.state == 'play':
            pos = self.sonido_actual.get_pos()
            dur = self.sonido_actual.length or 1
            ratio = min(pos / dur, 1.0)
            self.root_widget.ids.prog_widget.progress = ratio
            self.root_widget.ids.lbl_tiempo.text    = self._fmt(pos)
            self.root_widget.ids.lbl_duracion.text  = self._fmt(dur)

    def _fmt(self, seg):
        seg = max(int(seg), 0)
        return f'{seg // 60}:{seg % 60:02d}'

    # ── MICRÓFONO / VOZ ─────────────────────────────────────────────────────

    COMANDOS = {
        'reproducir': ['play', 'reproduce', 'music', 'música', 'continúa', 'continua'],
        'pausar':     ['pausa', 'pause', 'para', 'detente'],
        'detener':    ['stop', 'detén', 'deten', 'detener', 'silencio', 'apaga', 'para todo'],
        'siguiente':  ['siguiente', 'next', 'adelante', 'salta', 'otra', 'próxima', 'proxima', 'avanza'],
        'anterior':   ['anterior', 'atrás', 'atras', 'back', 'regresa', 'vuelve', 'retrocede', 'previa', 'previo'],
        'subir_vol':  ['sube', 'más volumen', 'mas volumen', 'louder', 'más alto', 'mas alto', 'sube el volumen'],
        'bajar_vol':  ['baja', 'menos volumen', 'quieter', 'silencioso', 'más bajo', 'mas bajo', 'baja el volumen'],
    }

    COMANDOS_PLAY = ['play', 'reproduce', 'reproducir', 'toca', 'pon', 'inicia', 'empieza', 'comienza', 'música', 'musica']
    COMANDOS_PAUSAR = ['pausa', 'pause', 'para', 'espera', 'suspende']

    def toggle_microfono(self):
        self.mic_activo = not self.mic_activo
        if self.mic_activo:
            self.root_widget.ids.btn_mic.text = '🎙  VOZ: ACTIVA'
            self._set_mic_ui(True, 'ESPERANDO ORDEN...')
            if ANDROID:
                self._iniciar_reconocimiento()
            else:
                # Modo demo: simular escucha
                self._set_mic_ui(True, 'SIMULANDO ESCUCHA...')
        else:
            self.root_widget.ids.btn_mic.text = '🎙  ACTIVAR VOZ'
            self._set_mic_ui(False, 'MICRÓFONO: INACTIVO')
            if ANDROID:
                self._detener_reconocimiento()

    def _set_mic_ui(self, activo, texto):
        lbl  = self.root_widget.ids.lbl_mic_status
        lbl2 = self.root_widget.ids.lbl_mic_comando
        lbl.text  = texto
        lbl.color = (0.65, 0.15, 1, 1) if activo else (0.45, 0.45, 0.45, 1)
        if activo:
            lbl2.text  = 'di: siguiente · pausa · stop · sube · baja'
            lbl2.color = (0.55, 0, 0.85, 0.9)
        else:
            lbl2.text  = 'di: siguiente · pausa · stop'
            lbl2.color = (0.4, 0, 0.6, 0.8)

    def _iniciar_reconocimiento(self):
        """Lanzar SpeechRecognizer en el UI thread de Android (obligatorio)."""
        try:
            Handler = autoclass('android.os.Handler')
            Looper  = autoclass('android.os.Looper')
            Handler(Looper.getMainLooper()).post(_Runnable(self._setup_recognizer))
        except Exception as e:
            self._set_mic_ui(False, f'MIC ERROR: {str(e)[:28]}')
            self.mic_activo = False

    def _setup_recognizer(self):
        """Se ejecuta en el UI thread de Android."""
        try:
            # Destruir recognizer anterior
            if self._recognizer:
                try:
                    self._recognizer.stopListening()
                    self._recognizer.destroy()
                except Exception:
                    pass
                self._recognizer = None

            PythonActivity   = autoclass('org.kivy.android.PythonActivity')
            SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
            Intent           = autoclass('android.content.Intent')
            RecognizerIntent = autoclass('android.speech.RecognizerIntent')

            activity = PythonActivity.mActivity
            self._recognizer = SpeechRecognizer.createSpeechRecognizer(activity)
            self._voice_listener = YAMIVoiceListener(self)
            self._recognizer.setRecognitionListener(self._voice_listener)

            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es")
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "es")
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5)
            intent.putExtra(
                RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500)
            intent.putExtra(
                RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 300)
            intent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE,
                            activity.getPackageName())

            self._recognizer.startListening(intent)
        except Exception as e:
            Clock.schedule_once(lambda dt, err=str(e):
                self._set_mic_ui(False, f'MIC ERROR: {err[:28]}'), 0)
            Clock.schedule_once(lambda dt: setattr(self, 'mic_activo', False), 0)

    def _detener_reconocimiento(self):
        if not self._recognizer:
            return
        rec = self._recognizer
        self._recognizer = None
        try:
            Handler = autoclass('android.os.Handler')
            Looper  = autoclass('android.os.Looper')
            def _stop():
                try:
                    rec.stopListening()
                    rec.destroy()
                except Exception:
                    pass
            Handler(Looper.getMainLooper()).post(_Runnable(_stop))
        except Exception:
            pass

    def _on_voice_error(self, error):
        # Error 7 = no match, error 6 = no speech — reiniciar silenciosamente
        if error in (6, 7) and self.mic_activo:
            Clock.schedule_once(lambda dt: self._iniciar_reconocimiento(), 1.0)
        else:
            self._set_mic_ui(False, f'VOZ ERROR: {error}')
            self.mic_activo = False

    def procesar_comando_voz(self, texto: str):
        """Interpreta el texto reconocido y ejecuta la acción."""
        t = texto.lower().strip()
        self._set_mic_ui(True, f'ORDEN: "{texto[:22]}"')
        Clock.schedule_once(
            lambda dt: self._set_mic_ui(True, 'ESPERANDO ORDEN...'), 2.5
        )

        accion = None
        for cmd, palabras in self.COMANDOS.items():
            if any(p in t for p in palabras):
                accion = cmd
                break

        if accion == 'reproducir': self.reproducir()
        elif accion == 'pausar':   self.pausar()
        elif accion == 'detener':  self.detener()
        elif accion == 'siguiente':self.siguiente()
        elif accion == 'anterior': self.anterior()
        elif accion == 'subir_vol':
            slider = self.root_widget.ids.vol_slider
            slider.value = min(slider.value + 0.15, 1.0)
        elif accion == 'bajar_vol':
            slider = self.root_widget.ids.vol_slider
            slider.value = max(slider.value - 0.15, 0.0)
        else:
            self._set_mic_ui(True, 'ORDEN NO RECONOCIDA')

        # Re-escuchar automáticamente en Android
        if ANDROID and self.mic_activo:
            Clock.schedule_once(lambda dt: self._iniciar_reconocimiento(), 1.5)

    # ── ANDROID PERMISOS ────────────────────────────────────────────────────

    def _pedir_permisos(self, dt):
        try:
            from android.permissions import request_permissions, Permission
            VERSION = autoclass('android.os.Build$VERSION')
            if VERSION.SDK_INT >= 33:
                # Android 13+: READ_EXTERNAL_STORAGE ya no da acceso a audio
                perms = [
                    'android.permission.READ_MEDIA_AUDIO',
                    Permission.RECORD_AUDIO,
                ]
            else:
                perms = [
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.RECORD_AUDIO,
                ]
            request_permissions(perms, self._on_permisos_granted)
        except Exception as e:
            self._set_status(f'PERM: {str(e)[:25]}')
            Clock.schedule_once(self.cargar_biblioteca, 0.3)

    def _on_permisos_granted(self, permissions, results):
        """Callback al conceder permisos: recarga biblioteca con acceso real."""
        Clock.schedule_once(self.cargar_biblioteca, 0.3)

    # ── UTILS ────────────────────────────────────────────────────────────────

    def _set_status(self, texto: str):
        self.root_widget.ids.lbl_status.text = texto


if __name__ == '__main__':
    YAMI_Sonic_Autonomy().run()
