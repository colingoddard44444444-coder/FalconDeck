import tkinter as tk


class HomeScreen:
    def __init__(
        self,
        root,
        enter_callback,
        start_heartbeat=None,
        stop_heartbeat=None,
    ):
        self.root = root
        self.enter_callback = enter_callback
        self.stop_heartbeat = stop_heartbeat
        self.entered = False

        self.frame = tk.Frame(root, bg="#05080c")
        self.frame.pack(fill="both", expand=True)

        tk.Label(
            self.frame,
            text="FALCONDECK",
            fg="#00eaff",
            bg="#05080c",
            font=("DejaVu Sans", 38, "bold"),
        ).place(relx=0.5, rely=0.38, anchor="center")

        tk.Label(
            self.frame,
            text="AVIATION SYSTEM",
            fg="#9aa7b2",
            bg="#05080c",
            font=("DejaVu Sans", 11, "bold"),
        ).place(relx=0.5, rely=0.49, anchor="center")

        self.button = tk.Label(
            self.frame,
            text="ENTER",
            fg="#00eaff",
            bg="#10202c",
            font=("DejaVu Sans", 18, "bold"),
            width=12,
            height=2,
            relief="solid",
            bd=2,
        )
        self.button.place(relx=0.5, rely=0.68, anchor="center")

        tk.Label(
            self.frame,
            text="v1.2",
            fg="#64727c",
            bg="#05080c",
            font=("DejaVu Sans", 8),
        ).place(x=12, y=455)

        # Accept touchscreen press, mouse press, keyboard Enter or Space.
        self.root.bind_all("<ButtonPress-1>", self.enter)
        self.root.bind_all("<ButtonRelease-1>", self.enter)
        self.root.bind_all("<Return>", self.enter)
        self.root.bind_all("<KP_Enter>", self.enter)
        self.root.bind_all("<space>", self.enter)

        self.root.focus_force()

        if start_heartbeat:
            start_heartbeat()

    def enter(self, event=None):
        if self.entered:
            return

        self.entered = True
        print("ENTER ACTIVATED", flush=True)

        self.root.unbind_all("<ButtonPress-1>")
        self.root.unbind_all("<ButtonRelease-1>")
        self.root.unbind_all("<Return>")
        self.root.unbind_all("<KP_Enter>")
        self.root.unbind_all("<space>")

        if self.stop_heartbeat:
            self.stop_heartbeat()

        # Hide welcome screen, build menu immediately, then remove welcome frame.
        self.frame.pack_forget()

        try:
            self.enter_callback()
            print("MAIN MENU CREATED", flush=True)
        except Exception as error:
            print(f"MAIN MENU ERROR: {error}", flush=True)
            raise

        self.frame.destroy()
