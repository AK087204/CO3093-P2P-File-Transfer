import User
import uuid

def main():
    user = User.User(str(uuid.uuid4()), "Anonymous")
    x = int(input("Enter 1 to share, 2 to download, 3 to get scrape info of the file: "))
    if x == 1:
        magnet_link = user.share()
        print("Magnet link:", magnet_link)
    elif x == 2:
        user.download()
    elif x == 3:
        user.get_scrape()
    else:
        print("Invalid input")
main()
