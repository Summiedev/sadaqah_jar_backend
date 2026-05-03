#To intehrate stuff later
from sqlalchemy.orm import Session
from app.models.notification import Notification

def send_push_notification(device_token: str, message: str):
    
    print(f"Sending notification to {device_token}: {message}")




def create_notification(db: Session, user_id: int, title: str, message: str):

    notification = Notification(
        user_id=user_id,
        title=title,
        message=message
    )

    db.add(notification)
    db.commit()