from __future__ import annotations

import argparse
import math
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from realtime_audio.virtual_mic_control import (
    ControlSettings,
    ENDPOINT_ACTIVE,
    ENDPOINT_AVAILABLE,
    ENDPOINT_BUSY,
    ENDPOINT_DISCONNECTED,
    ENDPOINT_ERROR,
    ENDPOINT_UNKNOWN,
    InputDevice,
    STATE_ACTIVE,
    STATE_ERROR,
    STATE_STARTING,
    STATE_STOPPED,
    STATE_STOPPING,
    UserPreferences,
    VirtualMicController,
    load_preferences,
    save_preferences,
)


STATE_LABELS = {
    STATE_STOPPED: "Parado",
    STATE_STARTING: "Iniciando",
    STATE_ACTIVE: "Ativo",
    STATE_STOPPING: "Parando",
    STATE_ERROR: "Erro",
}

ENDPOINT_LABELS = {
    ENDPOINT_UNKNOWN: "Verificando",
    ENDPOINT_AVAILABLE: "Disponível",
    ENDPOINT_ACTIVE: "Conectado",
    ENDPOINT_DISCONNECTED: "Desconectado",
    ENDPOINT_BUSY: "Ocupado",
    ENDPOINT_ERROR: "Erro",
}

AGGRESSIVENESS_OPTIONS = {
    "Suave (α = 1,2)": 1.2,
    "Padrão (α = 1,5)": 1.5,
    "Intensa (α = 1,8)": 1.8,
}


def _dbfs(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-6))


class VirtualMicApp:
    def __init__(self, root: tk.Tk, controller: VirtualMicController) -> None:
        self.root = root
        self.controller = controller
        self.devices: list[InputDevice] = []
        self.device_by_label: dict[str, int] = {}
        self.closing = False
        self.close_deadline = 0.0

        loaded = load_preferences()
        self.preferences = loaded.preferences
        self.preference_warning = loaded.warning

        self.device_var = tk.StringVar()
        self.aggressiveness_var = tk.StringVar(
            value=self._aggressiveness_label(self.preferences.aggressiveness)
        )
        self.state_var = tk.StringVar(value="Parado")
        self.endpoint_var = tk.StringVar(value="Verificando")
        self.message_var = tk.StringVar(
            value=loaded.warning or "Carregando dispositivos de entrada..."
        )
        self.level_text_var = tk.StringVar(value="-120,0 dBFS")
        self.metric_vars = {
            "processed": tk.StringVar(value="0"),
            "sent": tk.StringVar(value="0"),
            "drops": tk.StringVar(value="0"),
            "underruns": tk.StringVar(value="0"),
            "overruns": tk.StringVar(value="0"),
            "write_errors": tk.StringVar(value="0"),
            "latency": tk.StringVar(value="--"),
        }

        self._build_window()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self._load_environment)
        self.root.after(100, self._poll_status)

    @staticmethod
    def _aggressiveness_label(value: float) -> str:
        return min(
            AGGRESSIVENESS_OPTIONS,
            key=lambda label: abs(AGGRESSIVENESS_OPTIONS[label] - value),
        )

    def _build_window(self) -> None:
        self.root.title("Microfone Virtual PTC")
        self.root.geometry("680x530")
        self.root.minsize(640, 500)

        container = ttk.Frame(self.root, padding=10)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)

        title = ttk.Label(
            container,
            text="Controle do Microfone Virtual PTC",
            font=("Segoe UI", 15, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")
        ttk.Label(
            container,
            text="STFT causal adaptativa, 16 kHz, blocos de 20 ms, ponte 2/4",
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))

        settings = ttk.LabelFrame(container, text="Operação", padding=8)
        settings.grid(row=2, column=0, sticky="ew")
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Microfone físico").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=4
        )
        self.device_combo = ttk.Combobox(
            settings,
            textvariable=self.device_var,
            state="readonly",
        )
        self.device_combo.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(settings, text="Agressividade").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=4
        )
        self.aggressiveness_combo = ttk.Combobox(
            settings,
            textvariable=self.aggressiveness_var,
            values=list(AGGRESSIVENESS_OPTIONS),
            state="readonly",
            width=22,
        )
        self.aggressiveness_combo.grid(row=1, column=1, sticky="w", pady=4)

        buttons = ttk.Frame(settings)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.start_button = ttk.Button(
            buttons,
            text="Iniciar",
            command=self._start,
            underline=0,
        )
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(
            buttons,
            text="Parar",
            command=self._stop,
            state="disabled",
            underline=0,
        )
        self.stop_button.pack(side="left", padx=(8, 0))
        ttk.Button(
            buttons,
            text="Atualizar dispositivos",
            command=self._load_environment,
        ).pack(side="right")

        status = ttk.LabelFrame(container, text="Estado", padding=8)
        status.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        status.columnconfigure(1, weight=1)
        ttk.Label(status, text="Operação").grid(row=0, column=0, sticky="w")
        ttk.Label(status, textvariable=self.state_var, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(status, text="Endpoint virtual").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(status, textvariable=self.endpoint_var).grid(
            row=1, column=1, sticky="w", pady=(4, 0)
        )
        ttk.Label(status, textvariable=self.message_var, wraplength=560).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        level = ttk.LabelFrame(container, text="Nível de entrada", padding=8)
        level.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        level.columnconfigure(0, weight=1)
        self.level_bar = ttk.Progressbar(level, maximum=100.0, mode="determinate")
        self.level_bar.grid(row=0, column=0, sticky="ew")
        ttk.Label(level, textvariable=self.level_text_var, width=13).grid(
            row=0, column=1, padx=(10, 0)
        )

        metrics = ttk.LabelFrame(container, text="Métricas", padding=8)
        metrics.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        labels = [
            ("Blocos processados", "processed"),
            ("Blocos enviados", "sent"),
            ("Descartes locais", "drops"),
            ("Underruns", "underruns"),
            ("Overruns", "overruns"),
            ("Erros de escrita", "write_errors"),
            ("Latência estimada", "latency"),
        ]
        for index, (label, key) in enumerate(labels):
            row = index // 2
            column = (index % 2) * 2
            ttk.Label(metrics, text=label).grid(
                row=row, column=column, sticky="w", padx=(0, 8), pady=1
            )
            ttk.Label(
                metrics,
                textvariable=self.metric_vars[key],
                font=("Segoe UI", 10, "bold"),
            ).grid(row=row, column=column + 1, sticky="w", padx=(0, 28), pady=1)

        ttk.Label(
            container,
            text="A latência exibida é uma estimativa por componentes, não uma medição física ponta a ponta.",
            foreground="#555555",
            wraplength=600,
        ).grid(row=6, column=0, sticky="w", pady=(6, 0))
        self.root.bind_all("<Alt-i>", lambda event: self.start_button.invoke())
        self.root.bind_all("<Alt-p>", lambda event: self.stop_button.invoke())
        self.root.bind_all("<F5>", lambda event: self._load_environment())

    def _load_environment(self) -> None:
        if self.closing:
            return
        self.message_var.set("Atualizando dispositivos e endpoint...")
        threading.Thread(
            target=self._load_environment_worker,
            name="ptc-ui-environment",
            daemon=True,
        ).start()

    def _load_environment_worker(self) -> None:
        try:
            devices = self.controller.list_input_devices()
            error = None
        except Exception as exc:
            devices = []
            error = f"Falha ao listar dispositivos: {exc}"
        self.controller.refresh_endpoint_status()
        self.root.after(0, lambda: self._apply_environment(devices, error))

    def _apply_environment(
        self,
        devices: list[InputDevice],
        error: str | None,
    ) -> None:
        if self.closing:
            return
        self.devices = devices
        self.device_by_label = {device.label: device.index for device in devices}
        labels = list(self.device_by_label)
        self.device_combo["values"] = labels
        preferred = self.preferences.input_device
        selected = next(
            (device.label for device in devices if device.index == preferred),
            labels[0] if labels else "",
        )
        self.device_var.set(selected)
        snapshot = self.controller.snapshot()
        if error:
            self.message_var.set(error)
        elif self.preference_warning:
            self.message_var.set(self.preference_warning)
            self.preference_warning = None
        else:
            self.message_var.set(snapshot.message)

    def _start(self) -> None:
        label = self.device_var.get()
        if label not in self.device_by_label:
            messagebox.showerror(
                "Microfone físico",
                "Selecione um dispositivo de entrada válido.",
            )
            return
        aggressiveness = AGGRESSIVENESS_OPTIONS[self.aggressiveness_var.get()]
        input_device = self.device_by_label[label]
        try:
            save_preferences(
                UserPreferences(
                    input_device=input_device,
                    aggressiveness=aggressiveness,
                )
            )
            self.preferences = UserPreferences(input_device, aggressiveness)
            self.controller.start(
                ControlSettings(
                    input_device=input_device,
                    aggressiveness=aggressiveness,
                )
            )
        except Exception as exc:
            messagebox.showerror("Microfone Virtual PTC", str(exc))

    def _stop(self) -> None:
        self.controller.stop()

    def _poll_status(self) -> None:
        snapshot = self.controller.snapshot()
        self.state_var.set(STATE_LABELS.get(snapshot.state, snapshot.state))
        self.endpoint_var.set(
            ENDPOINT_LABELS.get(snapshot.endpoint_status, snapshot.endpoint_status)
        )
        self.message_var.set(snapshot.message)
        self.metric_vars["processed"].set(str(snapshot.processed_blocks))
        self.metric_vars["sent"].set(str(snapshot.sent_blocks))
        self.metric_vars["drops"].set(str(snapshot.local_drops))
        self.metric_vars["underruns"].set(str(snapshot.underruns))
        self.metric_vars["overruns"].set(str(snapshot.overruns))
        self.metric_vars["write_errors"].set(str(snapshot.write_errors))
        latency = snapshot.estimated_latency_ms
        self.metric_vars["latency"].set(
            "--" if latency is None else f"{latency:.1f} ms (estimativa)"
        )
        level_db = _dbfs(snapshot.level_rms)
        self.level_text_var.set(f"{level_db:.1f} dBFS".replace(".", ","))
        self.level_bar["value"] = min(100.0, max(0.0, level_db + 100.0))

        active = snapshot.state in {STATE_STARTING, STATE_ACTIVE, STATE_STOPPING}
        has_device = self.device_var.get() in self.device_by_label
        self.start_button["state"] = (
            "disabled" if active or not has_device else "normal"
        )
        self.stop_button["state"] = (
            "normal" if snapshot.state in {STATE_STARTING, STATE_ACTIVE} else "disabled"
        )
        self.device_combo["state"] = "disabled" if active else "readonly"
        self.aggressiveness_combo["state"] = "disabled" if active else "readonly"

        if self.closing:
            if not self.controller.worker_alive or time.monotonic() >= self.close_deadline:
                self.root.destroy()
                return
        self.root.after(100, self._poll_status)

    def _on_close(self) -> None:
        if self.closing:
            return
        self.closing = True
        self.close_deadline = time.monotonic() + 3.0
        self.controller.stop()
        self.message_var.set("Encerrando com limite de 3 segundos...")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interface mínima de controle do Microfone Virtual PTC."
    )
    return parser.parse_args(argv)


def main() -> None:
    parse_args()
    root = tk.Tk()
    try:
        app = VirtualMicApp(root, VirtualMicController())
        root.mainloop()
        del app
    except Exception as exc:
        root.withdraw()
        messagebox.showerror("Microfone Virtual PTC", str(exc))
        root.destroy()


if __name__ == "__main__":
    main()
