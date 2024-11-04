import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import uuid
import User

class App:
    def __init__(self, root):
        self.root = root
        self.user = User.User(str(uuid.uuid4()), "Anonymous")
        self.root.title("Peer-to-Peer Application")
        self.root.geometry("400x300")

        # Share Button
        self.share_button = tk.Button(root, text="Share File/Folder", command=self.share)
        self.share_button.pack(pady=10)

        # Download Button
        self.download_button = tk.Button(root, text="Download from Torrent", command=self.download)
        self.download_button.pack(pady=10)

        # Scrape Button
        self.scrape_button = tk.Button(root, text="Get Scrape Info", command=self.scrape_info)
        self.scrape_button.pack(pady=10)

        # Stop Peer Button
        self.stop_button = tk.Button(root, text="Stop Peer by ID", command=self.stop_peer)
        self.stop_button.pack(pady=10)

        # Stop All Button
        self.stop_all_button = tk.Button(root, text="Stop All Peers", command=self.stop_all)
        self.stop_all_button.pack(pady=10)

    def share(self):
        # Hỏi người dùng muốn chọn tệp hay thư mục
        choice = messagebox.askyesno("Share", "Do you want to share a folder? (Choose 'No' to select a file)")

        # Nếu chọn chia sẻ thư mục
        if choice:
            path = filedialog.askdirectory(title="Select Directory")
        else:
            path = filedialog.askopenfilename(title="Select File")

        if path:
            magnet_link = self.user.share(path)
            messagebox.showinfo("Magnet Link", f"Magnet link: {magnet_link}")

    def download(self):
        # choice = messagebox.askyesno("Download", "Do you want to enter a Magnet Link? (Choose 'No' to select a Torrent File)")
        # if choice:
        #     magnet_link = simpledialog.askstring("Magnet Link", "Enter Magnet Link:")
        #     if magnet_link:
        #         self.user.download(magnet_link)
        #         messagebox.showinfo("Download", "Download started with Magnet Link!")
        # else:
            torrent_file = filedialog.askopenfilename(title="Select Torrent File")
            if torrent_file:
                self.user.download(torrent_file)
                messagebox.showinfo("Download", "Download started with Torrent File!")

    def scrape_info(self):
        choice = messagebox.askyesno("Scrape Info", "Do you want to enter a Magnet Link? (Choose 'No' to select a Torrent File)")
        if choice:
            magnet_link = simpledialog.askstring("Magnet Link", "Enter Magnet Link:")
            if magnet_link:
                self.user.scrape_tracker(magnet_link)
                messagebox.showinfo("Scrape Info", "Scrape info fetched with Magnet Link!")
        else:
            torrent_file = filedialog.askopenfilename(title="Select Torrent File")
            if torrent_file:
                self.user.scrape_tracker(torrent_file)
                messagebox.showinfo("Scrape Info", "Scrape info fetched with Torrent File!")

    def stop_peer(self):
        peer_id = simpledialog.askinteger("Peer ID", "Enter Peer ID to Stop:")
        if peer_id is not None:
            self.user.stop(peer_id)
            messagebox.showinfo("Stop Peer", f"Stopped peer with ID: {peer_id}")

    def stop_all(self):
        self.user.stop_all()
        messagebox.showinfo("Stop All", "All peers stopped successfully!")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
