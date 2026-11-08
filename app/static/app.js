// Funções comuns a todas as páginas. JavaScript puro, sem biblioteca.

// ------------------------------------------------------------ API ---------
// fetch + JSON. Se a API devolver erro, lança um Error com .detalhes.
async function api(url, opcoes = {}) {
  const resp = await fetch(url, opcoes);
  const corpo = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const e = new Error(corpo.erro || `Erro ${resp.status} em ${url}`);
    e.detalhes = corpo.detalhes || [];
    throw e;
  }
  return corpo;
}

// Envia um arquivo do <input type=file> como multipart (campo "arquivo").
function enviarArquivo(url, input) {
  const dados = new FormData();
  dados.append("arquivo", input.files[0]);
  return api(url, { method: "POST", body: dados });
}

// ------------------------------------------------------------ formatação --
const brl = v => v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const pct = v => v == null ? "—" : (100 * v).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + "%";
const num = v => v == null ? "—" : Number(v).toLocaleString("pt-BR");
// Datas exibidas como o banco gravou (horário do servidor Postgres), sem conversão de fuso.
const data = v => { if (!v) return "—"; const [d, h] = String(v).split("T"); const [a, m, di] = d.split("-"); return `${di}/${m}/${a} ${(h || "").slice(0, 5)}`; };

// Escapa texto antes de pôr no HTML (diagnósticos, nomes de arquivo...).
function esc(t) {
  return String(t ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ------------------------------------------------------------ mensagens ---
function mostrar(tipo, texto, detalhes = []) {
  const caixa = document.getElementById("mensagem");
  const lista = detalhes.length ? `<ul>${detalhes.map(d => `<li>${esc(d)}</li>`).join("")}</ul>` : "";
  caixa.innerHTML = `<div class="msg ${tipo}">${esc(texto)}${lista}</div>`;
}
const mostrarErro = e => mostrar("erro", e.message, e.detalhes || []);

// ------------------------------------------------------------ topo --------
async function montarTopo() {
  const paginas = [["/", "Painel"], ["/lotes", "Lotes"], ["/rotulos", "Rótulos"], ["/modelo", "Modelo"], ["/decisoes", "Decisões"]];
  const aqui = location.pathname;
  const links = paginas.map(([href, nome]) => `<a href="${href}" class="${href === aqui ? "ativo" : ""}">${nome}</a>`).join("");
  const topo = document.getElementById("topo");
  topo.innerHTML = `<div class="marca">Banco Aurora <small>Prevenção a Fraudes</small></div>
                    <nav>${links}</nav><div class="status" id="selo">verificando modelo…</div>`;
  try {
    const s = await api("/api/saude");
    const selo = document.getElementById("selo");
    if (s.modelo.ok) {
      selo.textContent = `modelo v${s.modelo.versao} · @champion · threshold ${s.modelo.threshold} · contrato v${s.contrato}`;
    } else {
      selo.textContent = `sem modelo em produção · contrato v${s.contrato}`;
      selo.classList.add("erro");
      selo.title = s.modelo.erro;
    }
    return s;
  } catch (e) {
    document.getElementById("selo").textContent = "sistema fora do ar";
  }
}
