"""
BodyTracker: classe para rastreamento espacial do corpo (esqueleto) usando
webcam + MediaPipe Pose Landmarker (Tasks API).

Segue o mesmo padrão do FaceTracker: a câmera é aberta e gerenciada
internamente pela classe. Você chama `tracker.track()` sem nenhum argumento
a cada tick do seu game loop, e lê a posição atualizada direto dos
atributos da instância (ex: `tracker.landmarks["left_wrist"]`).

Não usa `mediapipe.solutions` (API legada quebrada em vários builds recentes
do mediapipe no Windows/Python 3.13). Usa `mediapipe.tasks` (PoseLandmarker),
API oficial e ativamente mantida.

Instalação:
    pip install opencv-python mediapipe numpy

Uso básico (dentro de um game loop):
    tracker = BodyTracker(show_window=True)

    class Player:
        def tick(self):
            tracker.track()                     # única chamada, sem argumentos
            if tracker.body_detected:
                hip = tracker.landmarks["left_hip"]
                self.position = (hip.x, hip.y, hip.z)   # metros

    tracker.close()

Rode este arquivo diretamente para ver uma demonstração ao vivo:
    python body_tracker.py
"""

import os
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision


# ---------------------------------------------------------------------------
# Nomes amigáveis para os 33 landmarks do BlazePose (ordem oficial do MediaPipe)
# ---------------------------------------------------------------------------
POSE_LANDMARK_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear", "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_pinky", "right_pinky",
    "left_index", "right_index", "left_thumb", "right_thumb",
    "left_hip", "right_hip", "left_knee", "right_knee",
    "left_ankle", "right_ankle", "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]

# Conexões do esqueleto (pares de índices) para desenho e para montar o "rig"
SKELETON_CONNECTIONS = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
    ("left_ankle", "left_heel"), ("left_heel", "left_foot_index"),
    ("right_ankle", "right_heel"), ("right_heel", "right_foot_index"),
    ("nose", "left_ear"), ("nose", "right_ear"),
]


@dataclass
class Joint:
    """Posição de uma única articulação (landmark) do corpo."""
    x: float             # metros, eixo horizontal (direita +)
    y: float             # metros, eixo vertical (baixo +)
    z: float             # metros, profundidade relativa ao quadril (mais perto da câmera = negativo)
    visibility: float    # confiança de estar visível (0.0 - 1.0)
    px: int              # posição em pixels (x), útil para desenho/depuração
    py: int              # posição em pixels (y)


@dataclass
class BodyPose:
    """Resultado de uma leitura de pose corporal (esqueleto completo)."""
    landmarks: Dict[str, Joint] = field(default_factory=dict)
    # Posição ABSOLUTA do quadril (origem do esqueleto) relativa à câmera, em
    # metros. Diferente dos landmarks acima (que são relativos ao próprio
    # quadril), isto muda conforme você se afasta/aproxima da câmera.
    hip_position: Optional[Tuple[float, float, float]] = None
    frame: Optional[np.ndarray] = None   # frame BGR capturado


class BodyTracker:
    """
    Rastreador espacial de corpo (esqueleto) baseado em MediaPipe PoseLandmarker
    (Tasks API).

    A classe gerencia a webcam internamente: ao instanciar, a câmera já é
    aberta. Cada chamada a `track()` captura um novo frame sozinha, atualiza
    `self.landmarks` (dicionário nome -> Joint, em metros aproximados) e
    `self.body_detected`. Nenhum argumento é necessário.
    """

    MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
    )

    def __init__(
        self,
        camera_index: int = 0,
        model_path: Optional[str] = None,
        num_bodies: int = 1,
        mirror: bool = True,
        hold_last_pose: bool = True,
        show_window: bool = False,
        show_landmarks: bool = True,
        window_name: str = "BodyTracker - Preview",
    ):
        """
        Args:
            camera_index: índice da webcam a abrir (0 = padrão do sistema).
            model_path: caminho para o arquivo pose_landmarker_lite.task.
                        Se None, usa/baixa para a pasta deste script.
            num_bodies: número máximo de corpos a detectar.
            mirror: se True, espelha o frame horizontalmente (efeito selfie).
            hold_last_pose: se True (padrão), quando um frame não detecta o
                        corpo, `track()` mantém os últimos landmarks válidos
                        em vez de zerar tudo. Ideal para game loops.
            show_window: se True, abre uma janela do OpenCV mostrando a
                        câmera em paralelo, atualizada automaticamente a
                        cada chamada de `track()` (não bloqueia o game loop).
            show_landmarks: se True (padrão), desenha o esqueleto na janela
                        de preview. Se False, mostra a câmera "crua".
                        Só tem efeito quando `show_window=True`.
            window_name: título da janela de preview.
        """
        self._model_path = model_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "pose_landmarker_lite.task"
        )
        self._ensure_model()

        base_options = mp_tasks.BaseOptions(model_asset_path=self._model_path)
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=num_bodies,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)

        self._mirror = mirror
        self._hold_last_pose = hold_last_pose
        self._show_window = show_window
        self._show_landmarks = show_landmarks
        self._window_name = window_name

        self._last_pose: Optional[BodyPose] = None
        self._camera_matrix: Optional[np.ndarray] = None
        self._dist_coeffs = np.zeros((4, 1))

        # Estado público, sempre acessível como atributos (sem precisar
        # guardar o retorno de track()):
        self.landmarks: Dict[str, Joint] = {}
        self.hip_position: Optional[Tuple[float, float, float]] = None
        self.body_detected: bool = False

        # Abre a webcam automaticamente
        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Não foi possível abrir a câmera de índice {camera_index}."
            )

    # ------------------------------------------------------------------
    # Setup / utilitários internos
    # ------------------------------------------------------------------
    def _ensure_model(self):
        if not os.path.exists(self._model_path):
            print("Baixando modelo do MediaPipe (pose_landmarker_lite.task)... aguarde.")
            urllib.request.urlretrieve(self.MODEL_URL, self._model_path)
            print("Modelo baixado com sucesso:", self._model_path)

    # Índices de landmarks estáveis e centrais usados para resolver a
    # posição absoluta do quadril via solvePnP (ombros, quadris, joelhos).
    # São pontos que raramente ficam fora de quadro e têm boa visibilidade.
    _POSE_ANCHOR_NAMES = [
        "left_shoulder", "right_shoulder",
        "left_hip", "right_hip",
        "left_knee", "right_knee",
    ]

    @staticmethod
    def _build_camera_matrix(frame_width: int, frame_height: int) -> np.ndarray:
        focal_length = frame_width
        center = (frame_width / 2, frame_height / 2)
        return np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1],
        ], dtype=np.float64)

    def _solve_hip_position(
        self, landmarks: Dict[str, Joint], w: int, h: int, min_visibility: float = 0.5
    ) -> Optional[Tuple[float, float, float]]:
        """
        Calcula a posição ABSOLUTA do quadril (origem do esqueleto local)
        relativa à câmera, em metros, usando solvePnP.

        Ideia: `pose_world_landmarks` já são um esqueleto metricamente
        correto (em metros), porém centrado no quadril — não sabemos onde
        esse esqueleto está posicionado no espaço em frente à câmera. Ao
        casar esses pontos 3D (já em escala real) com os pixels 2D onde eles
        aparecem na imagem, o solvePnP resolve exatamente essa translação:
        o vetor resultante é a posição do centro do quadril relativa à
        câmera. Se você se afasta 3 metros, esse valor de Z cresce 3 metros.
        """
        object_points = []
        image_points = []
        for name in self._POSE_ANCHOR_NAMES:
            joint = landmarks.get(name)
            if joint is None or joint.visibility < min_visibility:
                continue
            object_points.append((joint.x, joint.y, joint.z))
            image_points.append((joint.px, joint.py))

        if len(object_points) < 6:
            # DLT (usado internamente pelo solvePnP) exige pelo menos 6 pontos
            # 3D-2D correspondentes; com menos que isso o OpenCV lança exceção.
            return None

        object_points = np.array(object_points, dtype=np.float64)
        image_points = np.array(image_points, dtype=np.float64)

        if self._camera_matrix is None:
            self._camera_matrix = self._build_camera_matrix(w, h)

        success_pnp, _, translation_vec = cv2.solvePnP(
            object_points,
            image_points,
            self._camera_matrix,
            self._dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not success_pnp:
            return None

        x, y, z = translation_vec.flatten()
        return float(x), float(y), float(z)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def track(self) -> Optional[BodyPose]:
        """
        Chamada ÚNICA por tick do seu game loop. Não recebe nenhum argumento.

        Captura um novo frame da webcam (gerenciada internamente pela classe),
        roda a detecção de pose e atualiza `self.landmarks` / `self.body_detected`.
        Nunca lança exceção por falha de detecção pontual.

        Uso típico dentro do tick de um objeto:
            def tick(self):
                tracker.track()
                if tracker.body_detected:
                    hip = tracker.landmarks["left_hip"]
                    self.position = (hip.x, hip.y, hip.z)

        Returns:
            BodyPose atual (nova detecção, ou a última pose válida se
            `hold_last_pose=True` e o frame atual não detectou corpo).
            Retorna None apenas se nenhum corpo jamais foi detectado ainda
            (ou hold_last_pose=False e o frame atual falhou).
        """
        success, frame = self._cap.read()
        if not success:
            self.body_detected = False
            return self._last_pose if self._hold_last_pose else None

        if self._mirror:
            frame = cv2.flip(frame, 1)

        h, w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        timestamp_ms = int(time.monotonic() * 1000)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        # pose_world_landmarks: coordenadas 3D em METROS, origem aprox. no
        # centro do quadril. pose_landmarks: coordenadas normalizadas (0-1)
        # usadas só para desenhar em pixels na tela.
        if not result.pose_world_landmarks or not result.pose_landmarks:
            self.body_detected = False
            return self._last_pose if self._hold_last_pose else None

        world_lms = result.pose_world_landmarks[0]
        pixel_lms = result.pose_landmarks[0]

        landmarks: Dict[str, Joint] = {}
        for idx, name in enumerate(POSE_LANDMARK_NAMES):
            wlm = world_lms[idx]
            plm = pixel_lms[idx]
            landmarks[name] = Joint(
                x=float(wlm.x), y=float(wlm.y), z=float(wlm.z),
                visibility=float(getattr(wlm, "visibility", 1.0)),
                px=int(plm.x * w), py=int(plm.y * h),
            )

        hip_position = self._solve_hip_position(landmarks, w, h)
        pose = BodyPose(landmarks=landmarks, hip_position=hip_position, frame=frame)

        # Atualiza estado interno / atributos de acesso rápido
        self._last_pose = pose
        self.landmarks = landmarks
        self.hip_position = hip_position
        self.body_detected = True

        if self._show_window:
            self._update_preview_window(pose)

        return pose

    def _update_preview_window(self, pose: Optional[BodyPose]):
        """Atualiza a janela de preview em paralelo (não bloqueante)."""
        if pose is None or pose.frame is None:
            return
        display_frame = pose.frame
        if self._show_landmarks:
            display_frame = _draw_skeleton_overlay(display_frame.copy(), pose)
        cv2.imshow(self._window_name, display_frame)
        cv2.waitKey(1)

    def show(self, enabled: bool = True):
        """
        Liga/desliga a janela de preview em tempo de execução, sem precisar
        recriar o tracker. Ex: tracker.show(True) / tracker.show(False).
        """
        self._show_window = enabled
        if not enabled:
            try:
                cv2.destroyWindow(self._window_name)
            except cv2.error:
                pass

    def close(self):
        """Libera a webcam, o modelo e fecha janelas abertas."""
        self._cap.release()
        self._landmarker.close()
        cv2.destroyAllWindows()

    # Suporte a uso com "with BodyTracker() as tracker:"
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ---------------------------------------------------------------------------
# Desenho do esqueleto (função de módulo, usada no preview e na demo)
# ---------------------------------------------------------------------------
def _draw_skeleton_overlay(frame, pose: BodyPose, min_visibility: float = 0.5):
    landmarks = pose.landmarks

    # Ossos (linhas entre articulações)
    for name_a, name_b in SKELETON_CONNECTIONS:
        a, b = landmarks.get(name_a), landmarks.get(name_b)
        if a and b and a.visibility >= min_visibility and b.visibility >= min_visibility:
            cv2.line(frame, (a.px, a.py), (b.px, b.py), (0, 255, 0), 2)

    # Articulações (pontos)
    for joint in landmarks.values():
        if joint.visibility >= min_visibility:
            cv2.circle(frame, (joint.px, joint.py), 4, (0, 0, 255), -1)

    # Texto com a posição ABSOLUTA do quadril relativa à câmera
    if pose.hip_position:
        hx, hy, hz = pose.hip_position
        cv2.putText(
            frame,
            f"Quadril abs (X,Y,Z) m: ({hx:6.3f}, {hy:6.3f}, {hz:6.3f})",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
        )
    return frame


# ---------------------------------------------------------------------------
# Demonstração ao vivo (executa apenas se rodar este arquivo direto)
# ---------------------------------------------------------------------------
def main():
    with BodyTracker(show_window=True, show_landmarks=True) as tracker:
        while True:
            tracker.track()   # única chamada, sem argumentos

            if tracker.body_detected:
                hx, hy, hz = tracker.hip_position or (0.0, 0.0, 0.0)
                wrist = tracker.landmarks["right_wrist"]
                print(
                    f"quadril_absoluto=({hx:.3f}, {hy:.3f}, {hz:.3f}) m   "
                    f"pulso_dir_relativo=({wrist.x:.3f}, {wrist.y:.3f}, {wrist.z:.3f}) m"
                )

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
