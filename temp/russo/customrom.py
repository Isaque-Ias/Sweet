from tracker import FaceTracker

tracker = FaceTracker()      # já abre a webcam sozinha
pose = tracker.track()       # captura o frame e retorna a pose, sem argumentos

print(pose.x, pose.y, pose.z)   # metros
print(pose.pitch, pose.yaw, pose.roll)  # graus

tracker.close()