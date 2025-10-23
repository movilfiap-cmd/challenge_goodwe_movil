"""
Sistema de Gerenciamento de Energia Inteligente
-------------------------------------------------

Este módulo implementa uma aplicação gráfica simples, construída com
``tkinter``, que demonstra como monitorar o consumo de energia de
dispositivos domésticos, ajustar automaticamente o limite de consumo
com base na previsão do tempo (via API da OpenWeather) e cadastrar
novos dispositivos de forma manual ou utilizando a plataforma Tuya.

Os requisitos para execução são mínimos: apenas Python 3 e a
biblioteca ``requests`` (já incluída na maioria das instalações). A
integração com a Tuya é opcional e depende da biblioteca ``tinytuya``.
Caso ela não esteja instalada ou a conexão com a Internet não esteja
disponível, a aplicação continua funcional, utilizando um modo
simulado para cadastro de dispositivos.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk



# Tentar importar a biblioteca tinytuya. Caso não esteja disponível
# (por exemplo, em ambientes sem acesso à internet para instalação),
# a variável ``tinytuya`` será ``None`` e o cadastro de dispositivos
# Tuya será tratado de forma simulada.
try:
    import tinytuya  # type: ignore
except Exception:
    tinytuya = None  # type: ignore


openweather_api_key = os.getenv("OPENWEATHER_API_KEY")

@dataclass
class Device:
    """Representa um dispositivo monitorado.

    Atributos:
        name: Nome amigável do dispositivo.
        device_id: Identificador único (pode ser o ID Tuya ou um nome
            inventado pelo usuário).
        last_consumption: Último consumo registrado em kWh. Este valor é
            atualizado ao ler o arquivo CSV com medições ou ao
            cadastrar um dispositivo manualmente.
        ip: Endereço IP local do dispositivo (opcional, utilizado pela
            plataforma Tuya).
        local_key: Chave local (opcional, utilizada pela plataforma
            Tuya).
    """

    name: str
    device_id: str
    last_consumption: float = 0.0
    ip: Optional[str] = None
    local_key: Optional[str] = None
    # Campo extra para armazenar uma instância do dispositivo Tuya se
    # ``tinytuya`` estiver disponível. Não é inicializado pelo
    # construtor para evitar problemas de serialização.
    tuya_device: Optional[object] = field(default=None, init=False, repr=False)


class EnergyManagerApp:
    """Aplicação principal para gerenciamento de energia.

    Esta classe encapsula toda a lógica da aplicação, incluindo a
    interface gráfica, leitura de dados de consumo, comunicação com
    a API de previsão do tempo da OpenWeather e cadastro de
    dispositivos (manuais e via Tuya).
    """

    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("Gerenciador de Energia Inteligente")

        # Diretório base onde os arquivos de dados se encontram. A
        # aplicação assume que ``leituras_sim.csv`` está localizado
        # neste diretório.
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # Chave da API da OpenWeather. Por padrão, utiliza a chave
        # fornecida nos requisitos; o usuário pode alterá-la em tempo
        # real pela interface.
        self.openweather_api_key: tk.StringVar = tk.StringVar(
            value=openweather_api_key
        )
        # Cidade/pais para consulta de previsão. Pode ser alterada.
        self.city_var: tk.StringVar = tk.StringVar(value="Sao Paulo,BR")

        # Limite básico de consumo (kWh). Este limite representa o
        # valor de referência para dias com alta incidência de luz
        # solar. O limite efetivo será multiplicado por um fator
        # calculado a partir da previsão do tempo.
        self.base_limit_kwh: tk.DoubleVar = tk.DoubleVar(value=5.0)
        # Fator aplicado ao limite base de acordo com a condição de
        # luminosidade. Começa em 1.0 (nenhum ajuste).
        self.limit_factor: float = 1.0

        # Estrutura de dados contendo os dispositivos cadastrados,
        # indexados pelo identificador. Ao iniciar, a aplicação
        # carrega dados do arquivo CSV para preencher esta lista.
        self.devices: Dict[str, Device] = {}
        self._load_consumption_data()

        # Criação dos elementos da interface gráfica
        self._create_widgets()
        self._refresh_treeview()
        self._update_limit_display()

    # ------------------------------------------------------------------
    # Carregamento de dados
    # ------------------------------------------------------------------
    def _load_consumption_data(self) -> None:
        """Lê o arquivo CSV e atualiza os consumos dos dispositivos.

        O arquivo ``leituras_sim.csv`` deve possuir três colunas:
        ``device_id``, ``timestamp`` e ``consumo_kwh``. A função
        agrupa os valores por dispositivo, armazenando o último
        consumo registrado. Caso o arquivo não exista, uma mensagem
        informativa é apresentada e nenhum dispositivo é carregado.
        """
        csv_path = os.path.join(self.base_dir, "leituras_sim.csv")
        if not os.path.exists(csv_path):
            messagebox.showwarning(
                "Dados ausentes",
                (
                    f"O arquivo de leituras '{csv_path}' não foi encontrado.\n"
                    "Você poderá cadastrar dispositivos manualmente pela interface."
                ),
            )
            return

        data_per_device: Dict[str, List[float]] = {}
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    dev = row.get("device_id") or row.get("Device")
                    if not dev:
                        continue
                    try:
                        cons = float(row.get("consumo_kwh") or row.get("consumo") or 0)
                    except ValueError:
                        cons = 0.0
                    data_per_device.setdefault(dev, []).append(cons)
        except Exception as exc:
            messagebox.showerror(
                "Erro de leitura",
                f"Não foi possível ler o arquivo de leituras: {exc}",
            )
            return

        # Atualizar ou criar dispositivos com o último consumo
        for device_id, values in data_per_device.items():
            last = values[-1] if values else 0.0
            if device_id in self.devices:
                self.devices[device_id].last_consumption = last
            else:
                self.devices[device_id] = Device(name=device_id, device_id=device_id, last_consumption=last)

    # ------------------------------------------------------------------
    # Interface gráfica
    # ------------------------------------------------------------------
    def _create_widgets(self) -> None:
        """Configura todos os elementos da interface gráfica."""
        # Frame superior para configurações de API e cidade
        config_frame = ttk.Frame(self.master)
        config_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(config_frame, text="Chave OpenWeather:").grid(row=0, column=0, sticky=tk.W)
        api_entry = ttk.Entry(config_frame, textvariable=self.openweather_api_key, width=40)
        api_entry.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(config_frame, text="Cidade:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        city_entry = ttk.Entry(config_frame, textvariable=self.city_var, width=20)
        city_entry.grid(row=0, column=3, sticky=tk.W, padx=5)

        # Botão para atualizar previsão e ajustar limite
        weather_btn = ttk.Button(
            config_frame,
            text="Atualizar Previsão",
            command=self._fetch_and_adjust_limit,
        )
        weather_btn.grid(row=0, column=4, sticky=tk.W, padx=(20, 0))

        # Frame para exibição do limite de consumo e consumo atual
        self.limit_frame = ttk.Frame(self.master)
        self.limit_frame.pack(fill=tk.X, padx=10, pady=5)
        self.limit_var = tk.StringVar()
        self.limit_label = ttk.Label(
            self.limit_frame,
            textvariable=self.limit_var,
            font=("Arial", 12, "bold"),
        )
        self.limit_label.pack(side=tk.LEFT)

        # Permitir ao usuário ajustar o limite base manualmente
        adjust_frame = ttk.Frame(self.master)
        adjust_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(adjust_frame, text="Limite base (kWh):").pack(side=tk.LEFT)
        base_limit_entry = ttk.Spinbox(
            adjust_frame,
            from_=1.0,
            to=100.0,
            increment=0.5,
            textvariable=self.base_limit_kwh,
            width=5,
            command=self._update_limit_display,
        )
        base_limit_entry.pack(side=tk.LEFT, padx=5)

        # Treeview para listar dispositivos e consumos
        tree_frame = ttk.Frame(self.master)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        columns = ("device_name", "last_consumption")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("device_name", text="Dispositivo")
        self.tree.heading("last_consumption", text="Último Consumo (kWh)")
        self.tree.column("device_name", width=200)
        self.tree.column("last_consumption", width=150, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Barra de rolagem vertical para o treeview
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Frame inferior para botões de ação
        button_frame = ttk.Frame(self.master)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        add_btn = ttk.Button(
            button_frame,
            text="Cadastrar Dispositivo Manualmente",
            command=self._prompt_add_device,
        )
        add_btn.pack(side=tk.LEFT, padx=5)

        tuya_btn = ttk.Button(
            button_frame,
            text="Cadastrar Dispositivo via Tuya",
            command=self._prompt_add_tuya_device,
        )
        tuya_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = ttk.Button(
            button_frame,
            text="Recarregar Dados de Consumo",
            command=self._reload_consumption_file,
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)

    # ------------------------------------------------------------------
    # Funções de interface
    # ------------------------------------------------------------------
    def _refresh_treeview(self) -> None:
        """Atualiza o conteúdo do treeview com a lista de dispositivos."""
        # Limpar itens existentes
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Inserir dispositivos atuais
        for device in self.devices.values():
            self.tree.insert(
                "",
                tk.END,
                values=(device.name, f"{device.last_consumption:.2f}"),
            )

    def _update_limit_display(self) -> None:
        """Recalcula e exibe o limite de consumo e o total atual."""
        total_consumption = sum(d.last_consumption for d in self.devices.values())
        current_limit = self.base_limit_kwh.get() * self.limit_factor
        self.limit_var.set(
            (
                f"Limite de Consumo: {current_limit:.2f} kWh  |  "
                f"Consumo Atual: {total_consumption:.2f} kWh"
            )
        )
        # Mudar cor de texto conforme consumo supera o limite
        if total_consumption > current_limit:
            self.limit_label.config(foreground="red")
        else:
            self.limit_label.config(foreground="green")

    # ------------------------------------------------------------------
    # Operações com dispositivos
    # ------------------------------------------------------------------
    def _prompt_add_device(self) -> None:
        """Exibe uma janela de diálogo para cadastrar um dispositivo manualmente."""
        dialog = tk.Toplevel(self.master)
        dialog.title("Cadastrar Dispositivo Manualmente")
        dialog.grab_set()

        ttk.Label(dialog, text="Nome do dispositivo:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Identificador (opcional):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        id_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=id_var).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Consumo inicial (kWh):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        cons_var = tk.DoubleVar(value=0.0)
        ttk.Entry(dialog, textvariable=cons_var).grid(row=2, column=1, padx=5, pady=5)

        def on_confirm() -> None:
            name = name_var.get().strip() or None
            device_id = id_var.get().strip() or name
            try:
                consumption = float(cons_var.get())
            except Exception:
                consumption = 0.0
            if not name:
                messagebox.showwarning("Dados incompletos", "Informe um nome para o dispositivo.")
                return
            if device_id in self.devices:
                messagebox.showerror("Conflito", "Já existe um dispositivo com esse identificador.")
                return
            self.devices[device_id] = Device(name=name, device_id=device_id, last_consumption=consumption)
            dialog.destroy()
            self._refresh_treeview()
            self._update_limit_display()

        ttk.Button(dialog, text="Cancelar", command=dialog.destroy).grid(row=3, column=0, padx=5, pady=10)
        ttk.Button(dialog, text="Salvar", command=on_confirm).grid(row=3, column=1, padx=5, pady=10)

    def _prompt_add_tuya_device(self) -> None:
        """Exibe uma janela de diálogo para cadastrar um dispositivo via Tuya.

        Se a biblioteca ``tinytuya`` estiver disponível, tenta criar uma
        instância de dispositivo para validar os dados informados. Caso
        contrário, simula o cadastro apenas armazenando os parâmetros
        fornecidos.
        """
        dialog = tk.Toplevel(self.master)
        dialog.title("Cadastrar Dispositivo via Tuya")
        dialog.grab_set()

        ttk.Label(dialog, text="Nome do dispositivo:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Device ID:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        id_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=id_var).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Local Key:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        key_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=key_var).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="IP Local:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ip_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=ip_var).grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Consumo inicial (kWh):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        cons_var = tk.DoubleVar(value=0.0)
        ttk.Entry(dialog, textvariable=cons_var).grid(row=4, column=1, padx=5, pady=5)

        def on_confirm() -> None:
            name = name_var.get().strip() or None
            device_id = id_var.get().strip()
            local_key = key_var.get().strip() or None
            ip = ip_var.get().strip() or None
            try:
                consumption = float(cons_var.get())
            except Exception:
                consumption = 0.0
            if not name or not device_id:
                messagebox.showwarning("Dados incompletos", "Informe pelo menos o nome e o Device ID.")
                return
            if device_id in self.devices:
                messagebox.showerror("Conflito", "Já existe um dispositivo com esse Device ID.")
                return
            # Se tinytuya estiver disponível, tentar inicializar o dispositivo
            tuya_dev = None
            if tinytuya is not None and ip and local_key:
                try:
                    tuya_dev = tinytuya.OutletDevice(device_id, ip, local_key)
                    # Definimos a versão mais comum; em um sistema real
                    # convém detectar a versão correta.
                    tuya_dev.set_version(3.3)
                except Exception as exc:
                    messagebox.showwarning(
                        "Falha na conexão",
                        (
                            f"Não foi possível inicializar o dispositivo Tuya: {exc}\n"
                            "O dispositivo será cadastrado apenas localmente."
                        ),
                    )
                    tuya_dev = None
            elif tinytuya is None:
                messagebox.showinfo(
                    "Modo simulado",
                    (
                        "A biblioteca tinytuya não está instalada.\n"
                        "O dispositivo será cadastrado apenas localmente."
                    ),
                )
            # Criar instância de Device e armazenar
            dev = Device(name=name, device_id=device_id, last_consumption=consumption, ip=ip, local_key=local_key)
            dev.tuya_device = tuya_dev
            self.devices[device_id] = dev
            dialog.destroy()
            self._refresh_treeview()
            self._update_limit_display()

        ttk.Button(dialog, text="Cancelar", command=dialog.destroy).grid(row=5, column=0, padx=5, pady=10)
        ttk.Button(dialog, text="Salvar", command=on_confirm).grid(row=5, column=1, padx=5, pady=10)

    # ------------------------------------------------------------------
    # Atualização de leituras
    # ------------------------------------------------------------------
    def _reload_consumption_file(self) -> None:
        """Recarrega o arquivo de leituras e atualiza o treeview."""
        self._load_consumption_data()
        self._refresh_treeview()
        self._update_limit_display()

    # ------------------------------------------------------------------
    # Integração com OpenWeather
    # ------------------------------------------------------------------
    def _fetch_and_adjust_limit(self) -> None:
        """Consulta a previsão do tempo e ajusta o limite de consumo.

        A função utiliza a API de previsão de 5 dias/3 horas da
        OpenWeather para estimar a incidência de luz solar nas
        próximas 24 horas. Se a maioria das condições for ``Clear``,
        considera-se alta incidência (aumenta-se o limite em 20%).
        Caso contrário (``Clouds``, ``Rain`` ou ``Drizzle``), reduz-se
        o limite em 20%. A chave de API e a cidade são lidas dos
        campos de entrada da interface.
        """
        api_key = self.openweather_api_key.get().strip()
        city = self.city_var.get().strip()
        if not api_key:
            messagebox.showwarning(
                "Chave ausente",
                "Informe uma chave da API OpenWeather para consultar a previsão.",
            )
            return
        if not city:
            messagebox.showwarning(
                "Cidade ausente",
                "Informe uma cidade (por exemplo, 'Sao Paulo,BR').",
            )
            return

        url = (
            "https://api.openweathermap.org/data/2.5/forecast?q="
            f"{city}&appid={api_key}&lang=pt_br&units=metric"
        )
        try:
            response = requests.get(url, timeout=10)
            # Converter para JSON independentemente do código de status
            data = response.json()
        except Exception as exc:
            messagebox.showerror("Erro de conexão", f"Falha ao consultar a API: {exc}")
            return

        # Verificar retorno
        if response.status_code != 200:
            message = data.get("message", "Erro desconhecido")
            messagebox.showerror(
                "Falha na API",
                f"Código {response.status_code}: {message}",
            )
            return

        # Extrair condições das próximas 8 previsões (24h) ou menos se
        # houver menos entradas
        forecasts: List[Dict] = data.get("list", [])[:8]
        conditions: List[str] = []
        for item in forecasts:
            weather_list = item.get("weather", [])
            if not weather_list:
                continue
            # A API retorna uma lista; pegamos o primeiro elemento
            main_cond = weather_list[0].get("main", "")
            conditions.append(main_cond)
        if not conditions:
            messagebox.showwarning(
                "Dados insuficientes",
                "Não foi possível extrair condições meteorológicas da resposta da API.",
            )
            return

        # Contar ocorrências de cada condição principal
        clear_count = sum(1 for c in conditions if c.lower() == "clear")
        cloudy_count = sum(1 for c in conditions if c.lower() == "clouds")
        rain_count = sum(1 for c in conditions if c.lower() in ("rain", "drizzle"))
        # Determinar incidência de luz solar
        if clear_count >= cloudy_count + rain_count:
            # Alta incidência de luz solar → aumentar limite em 20%
            self.limit_factor = 1.2
            summary = "Alta"
        else:
            # Baixa incidência (muitas nuvens ou chuva) → reduzir limite em 20%
            self.limit_factor = 0.8
            summary = "Baixa"
        # Atualizar exibição do limite
        self._update_limit_display()
        # Informar o usuário sobre a decisão
        cond_str = ", ".join(conditions)
        messagebox.showinfo(
            "Previsão analisada",
            (
                f"Condições previstas para as próximas horas: {cond_str}.\n"
                f"Incidência de luz solar considerada: {summary}.\n"
                f"O limite de consumo foi ajustado para {self.base_limit_kwh.get() * self.limit_factor:.2f} kWh."
            ),
        )


        

    # ------------------------------------------------------------------
    # Função de inicialização da aplicação
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Inicia o loop principal da interface gráfica."""
        self.master.mainloop()



def main() -> None:
    root = tk.Tk()
    app = EnergyManagerApp(root)
    app.run()



if __name__ == "__main__":
    main()