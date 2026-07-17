// Componente de autocomplete de categoria/subcategoria (research.md #16/#18
// da feature 008) -- compartilhado entre /ver/pendentes (US1) e
// nota_detalhe.html (US4). Um único campo de texto filtra, no navegador, a
// lista já carregada de categorias/subcategorias (sem endpoint de busca
// novo); ao não encontrar correspondência e apertar Enter, oferece criar a
// subcategoria ali mesmo (perguntando a categoria-pai).

function normalizarTextoBusca(s) {
  return s.trim().toLowerCase();
}

function construirOpcoesCategoria(categorias) {
  const porId = new Map(categorias.map((c) => [c.id, c]));
  return categorias.map((c) => {
    if (c.parent_id === null) {
      return { id: c.id, rotulo: c.nome };
    }
    const pai = porId.get(c.parent_id);
    return { id: c.id, rotulo: `${pai ? pai.nome : "?"} › ${c.nome}` };
  });
}

async function recarregarCategorias(apiBase) {
  const resposta = await fetch(`${apiBase}/categorias`);
  const corpo = await resposta.json();
  return corpo.categorias;
}

async function criarSubcategoriaInline(nomeSubcategoria, categoriasAtuais, apiBase) {
  const nomePai = prompt(
    `Categoria "${nomeSubcategoria}" não encontrada. Qual a categoria-pai? (nome de uma existente, ou um nome novo)`
  );
  if (!nomePai || !nomePai.trim()) {
    return null;
  }

  const paiExistente = categoriasAtuais.find(
    (c) => c.parent_id === null && normalizarTextoBusca(c.nome) === normalizarTextoBusca(nomePai)
  );

  let paiId = paiExistente ? paiExistente.id : null;
  if (!paiId) {
    const respostaPai = await fetch(`${apiBase}/categorias`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome: nomePai.trim() }),
    });
    const corpoPai = await respostaPai.json();
    if (!respostaPai.ok) {
      alert(corpoPai.erro || corpoPai.aviso || "Não foi possível criar a categoria pai.");
      return null;
    }
    paiId = corpoPai.categoria.id;
  }

  return await criarCategoriaComAvisoDeQuaseDuplicata(nomeSubcategoria, paiId, apiBase);
}

async function criarCategoriaComAvisoDeQuaseDuplicata(nome, parentId, apiBase) {
  const resposta = await fetch(`${apiBase}/categorias`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome, parent_id: parentId }),
  });
  const corpo = await resposta.json();

  if (resposta.status === 409) {
    const usarSugestao = confirm(
      `${corpo.aviso} Sugestão: "${corpo.sugestao.nome}". Clique OK para usar a sugestão, ou Cancelar para criar "${nome}" mesmo assim.`
    );
    if (usarSugestao) {
      return corpo.sugestao.id;
    }
    const respostaForcada = await fetch(`${apiBase}/categorias`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome, parent_id: parentId, forcar: true }),
    });
    const corpoForcada = await respostaForcada.json();
    if (!respostaForcada.ok) {
      alert(corpoForcada.erro || "Não foi possível criar a subcategoria.");
      return null;
    }
    return corpoForcada.categoria.id;
  }

  if (!resposta.ok) {
    alert(corpo.erro || "Não foi possível criar a subcategoria.");
    return null;
  }
  return corpo.categoria.id;
}

// container: elemento com .categoria-input, .categoria-sugestoes e
// .categoria-id-selecionada. aoSelecionar(categoriaId): chamado sempre que
// uma categoria/subcategoria e selecionada ou criada com sucesso.
function inicializarAutocompleteCategoria(container, categoriasIniciais, apiBase, aoSelecionar) {
  const input = container.querySelector(".categoria-input");
  const sugestoesEl = container.querySelector(".categoria-sugestoes");
  const idEl = container.querySelector(".categoria-id-selecionada");
  let categorias = categoriasIniciais;
  let opcoes = construirOpcoesCategoria(categorias);

  function renderizarSugestoes(filtro) {
    const termo = normalizarTextoBusca(filtro);
    const encontradas = termo
      ? opcoes.filter((o) => normalizarTextoBusca(o.rotulo).includes(termo)).slice(0, 8)
      : [];
    sugestoesEl.innerHTML = "";
    if (!encontradas.length) {
      sugestoesEl.style.display = "none";
      return;
    }
    encontradas.forEach((opcao) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "list-group-item list-group-item-action py-1 px-2 text-sm";
      item.textContent = opcao.rotulo;
      item.addEventListener("click", () => {
        input.value = opcao.rotulo;
        idEl.value = opcao.id;
        sugestoesEl.style.display = "none";
        aoSelecionar(opcao.id);
      });
      sugestoesEl.appendChild(item);
    });
    sugestoesEl.style.display = "block";
  }

  input.addEventListener("input", () => {
    idEl.value = "";
    renderizarSugestoes(input.value);
  });

  input.addEventListener("keydown", async (evento) => {
    if (evento.key !== "Enter") return;
    evento.preventDefault();

    const termo = normalizarTextoBusca(input.value);
    const correspondencia = opcoes.find((o) => normalizarTextoBusca(o.rotulo) === termo);
    if (correspondencia) {
      input.value = correspondencia.rotulo;
      idEl.value = correspondencia.id;
      sugestoesEl.style.display = "none";
      aoSelecionar(correspondencia.id);
      return;
    }

    const nomeDigitado = input.value.trim();
    if (!nomeDigitado) return;

    const novaId = await criarSubcategoriaInline(nomeDigitado, categorias, apiBase);
    if (novaId) {
      categorias = await recarregarCategorias(apiBase);
      opcoes = construirOpcoesCategoria(categorias);
      const nova = opcoes.find((o) => o.id === novaId);
      input.value = nova ? nova.rotulo : nomeDigitado;
      idEl.value = novaId;
      sugestoesEl.style.display = "none";
      aoSelecionar(novaId);
    }
  });

  document.addEventListener("click", (evento) => {
    if (!container.contains(evento.target)) {
      sugestoesEl.style.display = "none";
    }
  });
}
