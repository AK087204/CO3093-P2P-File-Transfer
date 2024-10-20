import User
import uuid

def main():
    user = User.User(str(uuid.uuid4()), "Anonymous")
    x = int(input("Enter 1 to share, 2 to download: "))
    if x == 1:
        magnet_link = user.share()
        print("Magnet link:", magnet_link)
    elif x == 2:
        user.download()
    else:
        print("Invalid input")
main()
