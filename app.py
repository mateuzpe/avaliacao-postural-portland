import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import json
import io
from datetime import datetime
from fpdf import FPDF
from google import genai
from google.genai import types

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Avaliação Postural - Protocolo Portland",
    page_icon="🩺",
    layout="wide"
)

st.title("🩺 Sistema Digital de Avaliação Postural — Protocolo de Portland")
st.markdown("*Avaliação biomecânica assistida por Visão Computacional / IA Multimodal*")
st.divider()

# --- INICIALIZAÇÃO DE ESTADOS (SESSION STATE) ---
CRITERIOS_DEFAULT = {
    "cabeca_dorsal": 3,
    "ombros": 3,
    "escapulas": 3,
    "coluna_dorsal": 3,
    "bacia": 3,
    "cabeca_lateral": 3,
    "ombro_lateral": 3,
    "lordose": 3,
    "joelho_lateral": 3,
    "pe": 3
}

if "pontuacoes" not in st.session_state:
    st.session_state["pontuacoes"] = CRITERIOS_DEFAULT.copy()

if "justificativas_ia" not in st.session_state:
    st.session_state["justificativas_ia"] = ""

# --- SIDEBAR: Chave da API e Paciente ---
with st.sidebar:
    st.header("⚙️ Configurações & Paciente")
    api_key = st.text_input("Gemini API Key:", type="password", help="Chave gerada no Google AI Studio")
    
    st.subheader("📋 Dados do Avaliado")
    nome_paciente = st.text_input("Nome do Paciente:", "João Silva")
    idade = st.number_input("Idade:", min_value=1, max_value=120, value=25)
    genero = st.selectbox("Gênero:", ["Masculino", "Feminino", "Outro"])
    avaliador = st.text_input("Avaliador/Fisioterapeuta:", "Fisioterapeuta Responsável")

client = genai.Client(api_key=api_key) if api_key else None

LABEL_PONTOS = {
    3: "3 pts - Normal / Alinhado",
    2: "2 pts - Desvio Leve a Moderado",
    1: "1 pt - Desvio Acentuado / Crítico"
}

MAPA_NOMES = {
    "cabeca_dorsal": "Cabeça / Cervical (Dorsal)",
    "ombros": "Simetria de Ombros",
    "escapulas": "Escápulas / Torácica",
    "coluna_dorsal": "Coluna / Alinhamento",
    "bacia": "Nível de Bacia / Quadril",
    "cabeca_lateral": "Projeção de Cabeça (Lateral)",
    "ombro_lateral": "Projeção de Ombros (Lateral)",
    "lordose": "Lordose Lombar",
    "joelho_lateral": "Alinhamento dos Joelhos",
    "pe": "Arco Plantar / Pés"
}

# --- FUNÇÃO AUXILIAR: GERADOR DE PDF ---
def sanitizar_texto(texto: str) -> str:
    """Limpa emojis e markdown mantendo a acentuação em português para o PDF."""
    if not texto:
        return ""
    substituicoes = {
        "–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'",
        "•": "-", "…": "...", "🩺": "", "🟢": "", "🟡": "", "🟠": "",
        "🔴": "", "⚠️": "", "🚨": "", "🛑": "", "✅": "", "**": "",
        "*": "", "###": "", "##": "", "#": ""
    }
    for orig, subst in substituicoes.items():
        texto = texto.replace(orig, subst)
    return texto.encode("latin-1", "replace").decode("latin-1")


class PDFLaudo(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 8, "LAUDO DE AVALIAÇÃO POSTURAL — PROTOCOLO DE PORTLAND", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, "Sistema Digital de Triagem Biomecânica", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(180, 180, 180)
        self.line(10, 24, 200, 24)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}} | Documento de apoio diagnóstico", align="C")


def criar_pdf_relatorio(nome, idade, genero, avaliador, icp, status, pontuacao, scores, laudo_texto, fig_grafico):
    pdf = PDFLaudo(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 1. Metadados do Paciente
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(0, 0, 0)
    data_atual = datetime.now().strftime("%d/%m/%Y")
    
    pdf.cell(100, 6, sanitizar_texto(f"Paciente: {nome}"), border=0)
    pdf.cell(90, 6, sanitizar_texto(f"Data da Avaliação: {data_atual}"), border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(100, 6, sanitizar_texto(f"Idade: {idade} anos | Gênero: {genero}"), border=0)
    pdf.cell(90, 6, sanitizar_texto(f"Avaliador: {avaliador}"), border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 2. Caixa de Métricas
    pdf.set_fill_color(240, 244, 248)
    pdf.set_font("Helvetica", "B", 11)
    resumo_metricas = f"Pontuação Total: {pontuacao}/30 pts   |   ICP: {icp:.1f}%   |   Classificação: {status}"
    pdf.cell(0, 9, sanitizar_texto(resumo_metricas), border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 3. Tabela do Protocolo de Portland
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 225, 230)
    pdf.cell(90, 6, "Segmento / Critério Observado", border=1, fill=True)
    pdf.cell(30, 6, "Pontuação", border=1, align="C", fill=True)
    pdf.cell(70, 6, "Classificação do Segmento", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 8.5)
    for chave, nota in scores.items():
        desc_nome = MAPA_NOMES.get(chave, chave)
        status_regiao = "Normal / Alinhado" if nota == 3 else ("Desvio Moderado" if nota == 2 else "Desvio Severo")
        
        pdf.cell(90, 5.5, sanitizar_texto(desc_nome), border=1)
        pdf.cell(30, 5.5, f"{nota} pts", border=1, align="C")
        pdf.cell(70, 5.5, sanitizar_texto(status_regiao), border=1, new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(4)

    # 4. Inserção do Gráfico de Barras
    buf_img = io.BytesIO()
    fig_grafico.savefig(buf_img, format="png", dpi=180, bbox_inches="tight")
    buf_img.seek(0)
    pdf.image(buf_img, x=20, w=170)
    pdf.ln(2)

    # 5. Laudo Clínico Descritivo
    if laudo_texto:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "PARECER CLÍNICO & CONDUTA SUGERIDA", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5.5, sanitizar_texto(laudo_texto))

    return bytes(pdf.output())


# --- ABAS DA APLICAÇÃO ---
tab_fotos, tab_protocolo, tab_relatorio = st.tabs([
    "📸 1. Captura & Análise por IA",
    "📝 2. Matriz do Protocolo de Portland",
    "📊 3. Dashboard & Relatório"
])

# ==========================================
# ABA 1: FOTOS E ANÁLISE IA
# ==========================================
with tab_fotos:
    st.subheader("1. Carregamento de Fotografias Posturais")
    st.info("Envie a visão Posterior (Dorsal) e a visão Sagital (Lateral) do paciente.")

    col_img1, col_img2 = st.columns(2)
    with col_img1:
        st.markdown("**Visão Posterior (Dorsal)**")
        foto_dorsal = st.file_uploader("Foto Costas", type=["jpg", "jpeg", "png"], key="dorsal")
        if foto_dorsal:
            st.image(foto_dorsal, caption="Visão Dorsal Carregada", use_container_width=True)

    with col_img2:
        st.markdown("**Visão Sagital (Lateral)**")
        foto_lateral = st.file_uploader("Foto Perfil", type=["jpg", "jpeg", "png"], key="lateral")
        if foto_lateral:
            st.image(foto_lateral, caption="Visão Lateral Carregada", use_container_width=True)

    st.divider()

    if st.button("🤖 Executar Leitura Automática com Gemini Vision", type="primary"):
        if not client:
            st.error("Insira sua chave de API do Gemini na barra lateral antes de continuar.")
        elif not foto_dorsal and not foto_lateral:
            st.error("Por favor, envie ao menos uma foto (Dorsal ou Lateral).")
        else:
            with st.spinner("Analisando alinhamentos corporais sob o Protocolo de Portland..."):
                try:
                    conteudos = []
                    if foto_dorsal:
                        conteudos.append("Foto 1: Visão Posterior/Dorsal do paciente:")
                        conteudos.append(types.Part.from_bytes(data=foto_dorsal.getvalue(), mime_type=foto_dorsal.type))
                    if foto_lateral:
                        conteudos.append("Foto 2: Visão Lateral/Sagital do paciente:")
                        conteudos.append(types.Part.from_bytes(data=foto_lateral.getvalue(), mime_type=foto_lateral.type))

                    prompt_analise = """
                    Você é um especialista em biomecânica e avaliação postural.
                    Avalie a(s) imagem(ns) do paciente segundo o Protocolo de Portland (PSU).
                    Para cada um dos 10 itens abaixo, atribua nota inteira de 1 a 3 (3=Alinhado, 2=Desvio Leve, 1=Desvio Acentuado).
                    Se a vista correspondente não foi enviada, atribua nota 3.

                    Itens:
                    - cabeca_dorsal
                    - ombros
                    - escapulas
                    - coluna_dorsal
                    - bacia
                    - cabeca_lateral
                    - ombro_lateral
                    - lordose
                    - joelho_lateral
                    - pe

                    Retorne obrigatoriamente um objeto JSON com:
                    1. 'pontuacoes': dicionário com esses 10 itens e notas de 1 a 3.
                    2. 'justificativa': texto clínico explicando as assimetrias observadas.
                    """
                    conteudos.append(prompt_analise)

                    resposta = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=conteudos,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )

                    dados_json = json.loads(resposta.text)

                    if "pontuacoes" in dados_json:
                        for k, v in dados_json["pontuacoes"].items():
                            if k in st.session_state["pontuacoes"]:
                                st.session_state["pontuacoes"][k] = int(v)

                    st.session_state["justificativas_ia"] = dados_json.get("justificativa", "")
                    st.success("✅ Análise concluída! Os critérios na Aba 2 foram preenchidos automaticamente.")

                    with st.expander("Ver Parecer Clínico da IA", expanded=True):
                        st.markdown(st.session_state["justificativas_ia"])

                except Exception as e:
                    st.error(f"Erro ao processar com a IA: {e}")

# ==========================================
# ABA 2: FORMULÁRIO DO PROTOCOLO (REVISÃO)
# ==========================================
with tab_protocolo:
    st.subheader("2. Matriz Observacional de Portland")
    st.write("Confirme ou ajuste manualmente as notas atribuídas:")

    col_d, col_l = st.columns(2)

    with col_d:
        st.markdown("### 🔍 Visão Dorsal (Posterior)")
        for chave in ["cabeca_dorsal", "ombros", "escapulas", "coluna_dorsal", "bacia"]:
            st.session_state["pontuacoes"][chave] = st.selectbox(
                MAPA_NOMES[chave], [3, 2, 1],
                index=[3, 2, 1].index(st.session_state["pontuacoes"][chave]),
                format_func=lambda x: LABEL_PONTOS[x],
                key=f"sel_{chave}"
            )

    with col_l:
        st.markdown("### 🔍 Visão Lateral (Sagital)")
        for chave in ["cabeca_lateral", "ombro_lateral", "lordose", "joelho_lateral", "pe"]:
            st.session_state["pontuacoes"][chave] = st.selectbox(
                MAPA_NOMES[chave], [3, 2, 1],
                index=[3, 2, 1].index(st.session_state["pontuacoes"][chave]),
                format_func=lambda x: LABEL_PONTOS[x],
                key=f"sel_{chave}"
            )

    pontos_atuais = sum(st.session_state["pontuacoes"].values())
    icp_atual = (pontos_atuais / 30) * 100
    st.info(f"**Pontuação Consolidada:** {pontos_atuais}/30 | **ICP:** {icp_atual:.1f}%")

# ==========================================
# ABA 3: DASHBOARD & RELATÓRIO
# ==========================================
with tab_relatorio:
    st.subheader(f"Relatório Postural Consolidado — {nome_paciente}")

    pontos_totais = sum(st.session_state["pontuacoes"].values())
    icp = (pontos_totais / 30) * 100

    def classificar_icp(val):
        if val >= 85:
            return "Excelente / Postura Normal", "🟢"
        elif val >= 70:
            return "Bom / Desvios Leves", "🟡"
        elif val >= 50:
            return "Regular / Desvios Moderados", "🟠"
        else:
            return "Deficiente / Desvios Severos", "🔴"

    status_icp, icone = classificar_icp(icp)

    m1, m2, m3 = st.columns(3)
    m1.metric("Pontuação Total", f"{pontos_totais} / 30 pts")
    m2.metric("Índice Céfalo-Podal (ICP)", f"{icp:.1f}%")
    m3.metric("Classificação", f"{icone} {status_icp}")

    st.divider()

    df_grafico = pd.DataFrame([
        {"Região": MAPA_NOMES[k], "Pontuação": v}
        for k, v in st.session_state["pontuacoes"].items()
    ])

    col_g, col_c = st.columns([1.3, 1])

    fig, ax = plt.subplots(figsize=(6.5, 4))
    cores = ['#2ecc71' if p == 3 else '#f1c40f' if p == 2 else '#e74c3c' for p in df_grafico["Pontuação"]]
    ax.barh(df_grafico["Região"], df_grafico["Pontuação"], color=cores)
    ax.set_xlim(0, 3.5)
    ax.set_xlabel("Escore (1 a 3)")
    plt.tight_layout()

    with col_g:
        st.markdown("#### 📊 Distribuição Segmentar")
        st.pyplot(fig)

    with col_c:
        st.markdown("#### 🚨 Segmentos com Alerta")
        criticos = [MAPA_NOMES[k] for k, v in st.session_state["pontuacoes"].items() if v <= 2]
        if criticos:
            for item in criticos:
                ponto = [v for k, v in st.session_state["pontuacoes"].items() if MAPA_NOMES[k] == item][0]
                cor_alerta = "⚠️ Moderado" if ponto == 2 else "🛑 Severo"
                st.warning(f"**{item}** — {cor_alerta} (Nota {ponto})")
        else:
            st.success("Nenhuma alteração postural detectada! Todas as regiões pontuaram 3.")

    st.divider()

    # Botão para redigir laudo com Gemini
    if st.button("📄 Redigir Laudo Clínico Detalhado via Gemini"):
        if not client:
            st.error("Chave de API necessária na barra lateral.")
        else:
            with st.spinner("Gerando laudo clínico consolidado..."):
                prompt_laudo = f"""
                Escreva um laudo de Avaliação Postural baseado no Protocolo de Portland.
                
                Paciente: {nome_paciente} | Idade: {idade} anos | Gênero: {genero} | Avaliador: {avaliador}
                ICP: {icp:.1f}% ({status_icp}) | Pontos: {pontos_totais}/30
                
                Segmentos com desvio: {', '.join(criticos) if criticos else 'Nenhum desvio detectado'}
                Observações anatômicas: {st.session_state.get('justificativas_ia', 'Nenhuma imagem associada')}
                
                Divida em:
                1. Impressão Clínica Geral
                2. Detalhamento dos Segmentos com Desvio
                3. Recomendações e Condutas Terapêuticas (fortalecimento, RPG, ergonomia, etc.)
                """
                res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt_laudo)
                st.session_state["laudo_gerado"] = res.text

    if "laudo_gerado" in st.session_state:
        st.markdown("### 📝 Laudo Emitido")
        st.markdown(st.session_state["laudo_gerado"])

    # Exportação em PDF
    st.divider()
    st.subheader("📥 Exportação do Relatório")

    texto_laudo_export = st.session_state.get("laudo_gerado", "")

    pdf_bytes = criar_pdf_relatorio(
        nome=nome_paciente,
        idade=idade,
        genero=genero,
        avaliador=avaliador,
        icp=icp,
        status=status_icp,
        pontuacao=pontos_totais,
        scores=st.session_state["pontuacoes"],
        laudo_texto=texto_laudo_export,
        fig_grafico=fig
    )

    nome_arquivo_pdf = f"laudo_postural_{nome_paciente.replace(' ', '_').lower()}.pdf"

    st.download_button(
        label="📥 Baixar Relatório Completo em PDF",
        data=pdf_bytes,
        file_name=nome_arquivo_pdf,
        mime="application/pdf",
        type="primary"
    )

    plt.close(fig)
