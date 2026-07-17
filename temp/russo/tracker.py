"""
FaceTracker: classe para rastreamento espacial do rosto usando webcam + MediaPipe (Tasks API).

Não usa `mediapipe.solutions` (API legada quebrada em vários builds recentes
do mediapipe no Windows/Python 3.13). Usa `mediapipe.tasks` (FaceLandmarker),
API oficial e ativamente mantida.

A câmera é aberta automaticamente pela própria classe. Você não precisa
capturar o frame nem passar nada para o método `track()` — basta instanciar
e chamar `tracker.track()` sempre que quiser a posição atual do rosto.

Instalação:
    pip install opencv-python mediapipe numpy

Uso básico:
    tracker = FaceTracker()          # já abre a webcam internamente
    pose = tracker.track()           # captura um frame novo e retorna a pose
    print(pose.x, pose.y, pose.z)    # metros
    tracker.close()                  # libera webcam e modelo

Rode este arquivo diretamente para ver uma demonstração ao vivo:
    python face_tracker_v4.py
"""

import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision


@dataclass
class FacePose:
    """Resultado de uma leitura de pose facial."""
    x: float          # metros, eixo horizontal (direita +)
    y: float          # metros, eixo vertical (baixo +)
    z: float          # metros, distância da câmera (profundidade)
    pitch: float      # graus
    yaw: float        # graus
    roll: float       # graus
    landmarks_2d: np.ndarray   # pontos 2D usados no cálculo (pixels)
    frame: np.ndarray          # frame BGR capturado (útil para exibir/depurar)


class FaceTracker:
    """
    Rastreador espacial de rosto baseado em MediaPipe FaceLandmarker (Tasks API)
    + OpenCV solvePnP.

    A classe gerencia a webcam internamente: ao instanciar, a câmera já é
    aberta. Cada chamada a `track()` captura um novo frame sozinha e retorna
    a posição (x, y, z) em METROS, além dos ângulos de rotação da cabeça
    (pitch, yaw, roll). Nenhum argumento é necessário.
    """

    MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/1/face_landmarker.task"
    )

    # Modelo 3D genérico do rosto, em milímetros (proporções antropométricas médias).
    # Índices correspondem aos 478 landmarks do FaceLandmarker.
    _FACE_3D_MODEL_MM = np.array([
        (0.0, 0.0, 0.0),          # Ponta do nariz            -> landmark 1
        (0.0, -63.6, -12.5),      # Queixo                     -> landmark 152
        (-43.3, 32.7, -26.0),     # Canto do olho esquerdo     -> landmark 33
        (43.3, 32.7, -26.0),      # Canto do olho direito      -> landmark 263
        (-28.9, -28.9, -24.1),    # Canto da boca esquerdo     -> landmark 61
        (28.9, -28.9, -24.1),     # Canto da boca direito      -> landmark 291
    ], dtype=np.float64)

    _LANDMARK_IDS = [1, 152, 33, 263, 61, 291]

    def __init__(
        self,
        camera_index: int = 0,
        model_path: Optional[str] = None,
        num_faces: int = 1,
        mirror: bool = True,
        hold_last_pose: bool = True,
        show_window: bool = False,
        show_landmarks: bool = True,
        window_name: str = "FaceTracker - Preview",
    ):
        """
        Args:
            camera_index: índice da webcam a abrir (0 = padrão do sistema).
            model_path: caminho para o arquivo face_landmarker.task.
                        Se None, usa/baixa para a pasta deste script.
            num_faces: número máximo de rostos a detectar.
            mirror: se True, espelha o frame horizontalmente (efeito selfie).
            hold_last_pose: se True (padrão), quando um frame não detecta o
                        rosto (piscada, movimento rápido, etc.), `track()`
                        mantém e retorna a última pose válida em vez de None.
                        Ideal para game loops, evita "teleporte"/travamento
                        do objeto por falhas pontuais de detecção.
            show_window: se True, abre uma janela do OpenCV mostrando a
                        câmera em paralelo, atualizada automaticamente a cada
                        chamada de `track()` — sem bloquear o seu game loop
                        (o `cv2.waitKey(1)` interno só espera 1ms). Útil para
                        debugar visualmente enquanto o jogo roda.
            show_landmarks: se True (padrão), desenha os pontos do rosto e
                        o texto de posição/rotação na janela de preview.
                        Se False, mostra a câmera "crua", sem nenhuma UI.
                        Só tem efeito quando `show_window=True`.
            window_name: título da janela de preview.
        """
        self._model_path = model_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "face_landmarker.task"
        )
        self._ensure_model()

        base_options = mp_tasks.BaseOptions(model_asset_path=self._model_path)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=num_faces,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)

        self._mirror = mirror
        self._hold_last_pose = hold_last_pose
        self._dist_coeffs = np.zeros((4, 1))
        self._camera_matrix = None
        self._last_pose: Optional[FacePose] = None

        # Últimas coordenadas conhecidas, sempre acessíveis como atributos
        # (úteis para ler direto de dentro do tick do seu objeto, ex:
        # self.position = (tracker.x, tracker.y, tracker.z))
        self.x: float = 0.0
        self.y: float = 0.0
        self.z: float = 0.0
        self.pitch: float = 0.0
        self.yaw: float = 0.0
        self.roll: float = 0.0
        self.face_detected: bool = False

        self._show_window = show_window
        self._show_landmarks = show_landmarks
        self._window_name = window_name

        # Abre a webcam automaticamente
        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Não foi possível abrir a câmera de índice {camera_index}."
            )

        # Modelo 3D convertido para metros (facilita a saída final em metros)
        self._face_3d_model_m = self._FACE_3D_MODEL_MM / 1000.0

    # ------------------------------------------------------------------
    # Setup / utilitários internos
    # ------------------------------------------------------------------
    def _ensure_model(self):
        if not os.path.exists(self._model_path):
            print("Baixando modelo do MediaPipe (face_landmarker.task)... aguarde.")
            urllib.request.urlretrieve(self.MODEL_URL, self._model_path)
            print("Modelo baixado com sucesso:", self._model_path)

    @staticmethod
    def _build_camera_matrix(frame_width: int, frame_height: int) -> np.ndarray:
        focal_length = frame_width
        center = (frame_width / 2, frame_height / 2)
        return np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1],
        ], dtype=np.float64)

    @staticmethod
    def _rotation_matrix_to_euler_angles(R: np.ndarray) -> Tuple[float, float, float]:
        sy = np.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
        singular = sy < 1e-6
        if not singular:
            pitch = np.arctan2(R[2, 1], R[2, 2])
            yaw = np.arctan2(-R[2, 0], sy)
            roll = np.arctan2(R[1, 0], R[0, 0])
        else:
            pitch = np.arctan2(-R[1, 2], R[1, 1])
            yaw = np.arctan2(-R[2, 0], sy)
            roll = 0
        return np.degrees(pitch), np.degrees(yaw), np.degrees(roll)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def track(self) -> Optional[FacePose]:
        """
        Chamada ÚNICA por tick do seu game loop. Não recebe nenhum argumento.

        Captura um novo frame da webcam (gerenciada internamente pela classe),
        roda a detecção e atualiza a posição do rosto. Nunca lança exceção por
        falha de detecção pontual — projetada para ser chamada continuamente
        de dentro de um `Object.tick()`/loop de jogo sem precisar de try/except.

        Uso típico dentro do tick de um objeto:
            def tick(self):
                tracker.track()
                self.position = (tracker.x, tracker.y, tracker.z)

        Returns:
            FacePose atual (nova detecção, ou a última pose válida se
            `hold_last_pose=True` e o frame atual não detectou rosto).
            Retorna None apenas se nenhum rosto jamais foi detectado ainda
            (ou hold_last_pose=False e o frame atual falhou).
        """
        success, frame = self._cap.read()
        if not success:
            self.face_detected = False
            return self._last_pose if self._hold_last_pose else None

        if self._mirror:
            frame = cv2.flip(frame, 1)

        h, w = frame.shape[:2]
        if self._camera_matrix is None:
            self._camera_matrix = self._build_camera_matrix(w, h)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Timestamp monotônico em ms, exigido pelo modo VIDEO
        timestamp_ms = int(time.monotonic() * 1000)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        if not result.face_landmarks:
            self.face_detected = False
            return self._last_pose if self._hold_last_pose else None

        landmarks = result.face_landmarks[0]

        image_points = np.array([
            (landmarks[idx].x * w, landmarks[idx].y * h)
            for idx in self._LANDMARK_IDS
        ], dtype=np.float64)

        success_pnp, rotation_vec, translation_vec = cv2.solvePnP(
            self._face_3d_model_m,
            image_points,
            self._camera_matrix,
            self._dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        if not success_pnp:
            self.face_detected = False
            return self._last_pose if self._hold_last_pose else None

        rotation_mat, _ = cv2.Rodrigues(rotation_vec)
        pitch, yaw, roll = self._rotation_matrix_to_euler_angles(rotation_mat)
        x, y, z = translation_vec.flatten()  # já em metros (modelo 3D está em metros)

        pose = FacePose(
            x=float(x), y=float(y), z=float(z),
            pitch=float(pitch), yaw=float(yaw), roll=float(roll),
            landmarks_2d=image_points,
            frame=frame,
        )

        # Atualiza estado interno / atributos de acesso rápido
        self._last_pose = pose
        self.x, self.y, self.z = pose.x, pose.y, pose.z
        self.pitch, self.yaw, self.roll = pose.pitch, pose.yaw, pose.roll
        self.face_detected = True

        if self._show_window:
            self._update_preview_window(pose)

        return pose

    def _update_preview_window(self, pose: Optional[FacePose]):
        """Atualiza a janela de preview em paralelo (não bloqueante)."""
        if pose is None:
            return
        display_frame = pose.frame
        if self._show_landmarks:
            display_frame = _draw_pose_overlay(display_frame.copy(), pose)
        cv2.imshow(self._window_name, display_frame)
        # waitKey(1) apenas processa a fila de eventos da janela (~1ms),
        # não bloqueia o game loop chamador.
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

    # Suporte a uso com "with FaceTracker() as tracker:"
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ---------------------------------------------------------------------------
# Demonstração ao vivo (executa apenas se rodar este arquivo direto)
# ---------------------------------------------------------------------------
def _draw_pose_overlay(frame, pose: FacePose):
    for pt in pose.landmarks_2d:
        cv2.circle(frame, tuple(pt.astype(int)), 4, (0, 0, 255), -1)

    info_lines = [
        f"Posicao (X, Y, Z) m: ({pose.x:6.3f}, {pose.y:6.3f}, {pose.z:6.3f})",
        f"Rotacao P/Y/R graus: ({pose.pitch:6.1f}, {pose.yaw:6.1f}, {pose.roll:6.1f})",
    ]
    for i, line in enumerate(info_lines):
        cv2.putText(
            frame, line, (10, 30 + i * 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2,
        )
    return frame


def main():
    with FaceTracker() as tracker:
        while True:
            pose = tracker.track()   # sem argumentos - só chama e usa

            if pose is None:
                # Sem rosto detectado (ou falha de captura). Continua o loop.
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                continue

            print(
                f"x={pose.x:.3f} m  y={pose.y:.3f} m  z={pose.z:.3f} m  "
                f"pitch={pose.pitch:.1f}  yaw={pose.yaw:.1f}  roll={pose.roll:.1f}"
            )

            frame = _draw_pose_overlay(pose.frame, pose)
            cv2.imshow("FaceTracker - MediaPipe (Tasks API)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
