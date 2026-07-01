"""Harness visual local para o questionário extensionista.

Executa a página estática de docs/questionario em Chromium/Chrome, captura prints
em desktop e mobile e mede se a etapa ativa cabe no viewport após o
consentimento. Não envia respostas ao endpoint remoto.

Uso:
    python scripts/questionario_visual_harness.py

Saída:
    output/questionario_visual/*.png
    output/questionario_visual/metrics.json
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, Error, async_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "questionario" / "index.html"
OUT_DIR = ROOT / "output" / "questionario_visual"

VIEWPORTS = {
    "desktop_1920x1080": {"width": 1920, "height": 1080, "is_mobile": False},
    # Altura util real de um navegador maximizado (barras + SO comem ~120px).
    "desktop_1920x940": {"width": 1920, "height": 940, "is_mobile": False},
    "notebook_1366x768": {"width": 1366, "height": 768, "is_mobile": False},
    "notebook_1366x660": {"width": 1366, "height": 660, "is_mobile": False},
    "mobile_390x844": {"width": 390, "height": 844, "is_mobile": True},
}

QUESTION_TYPE_SELECTORS = {
    "checkbox": "input[type='checkbox']",
    "radio": "input[type='radio']",
    "audio-choice": "input[type='radio']",
    "scale": "input[type='radio']",
}


async def launch_browser() -> Browser:
    playwright = await async_playwright().start()
    launch_errors: list[str] = []
    for kwargs in ({}, {"channel": "chrome"}, {"channel": "msedge"}):
        try:
            browser = await playwright.chromium.launch(headless=True, **kwargs)
            browser._questionario_playwright = playwright  # type: ignore[attr-defined]
            return browser
        except Error as exc:
            launch_errors.append(str(exc).splitlines()[0])
    await playwright.stop()
    raise RuntimeError("Não foi possível abrir Chromium/Chrome/Edge: " + " | ".join(launch_errors))


async def measure(page, label: str) -> dict[str, Any]:
    return await page.evaluate(
        """
        (label) => {
          const rectOf = (selector) => {
            const element = document.querySelector(selector);
            if (!element) return null;
            const rect = element.getBoundingClientRect();
            return {
              top: Math.round(rect.top),
              bottom: Math.round(rect.bottom),
              left: Math.round(rect.left),
              right: Math.round(rect.right),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
              display: getComputedStyle(element).display,
              overflowY: getComputedStyle(element).overflowY,
              scrollHeight: Math.round(element.scrollHeight || 0),
              clientHeight: Math.round(element.clientHeight || 0),
            };
          };
          const html = document.documentElement;
          const body = document.body;
          const activeStep = document.querySelector('.wizard-step:not([hidden])');
          const activeRect = activeStep ? activeStep.getBoundingClientRect() : null;
          const footerRect = document.querySelector('.site-footer')?.getBoundingClientRect();
          const navRect = document.querySelector('.wizard-nav')?.getBoundingClientRect();
          const shellRect = document.querySelector('.wizard-shell')?.getBoundingClientRect();
          const headerRect = document.querySelector('.site-header')?.getBoundingClientRect();
          const viewportRect = document.querySelector('.wizard-viewport')?.getBoundingClientRect();
          const optionRow = activeStep ? activeStep.querySelector('.option-row') : null;
          const primaryButton = document.querySelector('.wizard-button--primary');
          const pageOverflow = html.scrollHeight > window.innerHeight + 2;
          const activeStepOverflow = activeStep ? activeStep.scrollHeight > activeStep.clientHeight + 2 : false;
          // Corte real: o passo e mais alto que a area util do viewport (overflow:hidden esconde a sobra).
          const viewportEl = document.querySelector('.wizard-viewport');
          const viewportClipPx = (viewportEl && activeStep)
            ? Math.max(0, Math.round(Math.max(activeStep.scrollHeight, activeStep.getBoundingClientRect().height) - viewportEl.clientHeight))
            : 0;
          const stepClipped = viewportClipPx > 2;
          // Escala efetiva: prova objetiva de que a UI "ficou maior".
          const bodyFontPx = Math.round(parseFloat(getComputedStyle(body).fontSize) * 10) / 10;
          // Alvo de toque (idosos/acessibilidade).
          const optionRowHeight = optionRow ? Math.round(optionRow.getBoundingClientRect().height) : null;
          const primaryButtonHeight = primaryButton ? Math.round(primaryButton.getBoundingClientRect().height) : null;
          // Gap constante entre o bloco da pergunta e a navegacao.
          const questionToNavGap = (viewportRect && navRect) ? Math.round(navRect.top - viewportRect.bottom) : null;
          // Aproveitamento vertical da area util (entre header e footer).
          const usableBand = (headerRect && footerRect) ? Math.round(footerRect.top - headerRect.bottom) : null;
          const activeBandUsage = (usableBand && activeRect) ? Math.round((activeRect.height / usableBand) * 100) / 100 : null;
          // Footer ancorado ao fundo do viewport (nao apenas "por acaso" dentro).
          const footerAnchored = Boolean(footerRect && Math.abs(footerRect.bottom - window.innerHeight) <= 2);
          return {
            label,
            viewport: { width: window.innerWidth, height: window.innerHeight },
            scroll: {
              pageYOffset: Math.round(window.pageYOffset),
              documentScrollHeight: Math.round(html.scrollHeight),
              bodyScrollHeight: Math.round(body.scrollHeight),
              pageOverflow,
              bodyOverflowY: getComputedStyle(body).overflowY,
            },
            activeMode: body.classList.contains('questionnaire-active'),
            scale: {
              bodyFontPx,
              optionRowHeight,
              primaryButtonHeight,
              questionToNavGap,
              usableBand,
              activeBandUsage,
            },
            introDisplay: getComputedStyle(document.querySelector('.intro-panel')).display,
            consentDisplay: getComputedStyle(document.querySelector('.consent-panel')).display,
            wizardShell: rectOf('.wizard-shell'),
            activeStep: rectOf('.wizard-step:not([hidden])'),
            questionCard: rectOf('.wizard-step:not([hidden]) .question-card'),
            audioPanel: rectOf('.wizard-step:not([hidden]) .audio-panel'),
            wizardNav: rectOf('.wizard-nav'),
            footer: rectOf('.site-footer'),
            checks: {
              footerWithinViewport: Boolean(footerRect && footerRect.bottom <= window.innerHeight + 1 && footerRect.top >= -1),
              footerAnchored,
              stepClipped,
              viewportClipPx,
              navWithinViewport: Boolean(navRect && navRect.bottom <= window.innerHeight + 1 && navRect.top >= -1),
              shellWithinViewport: Boolean(shellRect && shellRect.bottom <= window.innerHeight + 1 && shellRect.top >= -1),
              activeStepWithinViewport: Boolean(activeRect && activeRect.bottom <= window.innerHeight + 1 && activeRect.top >= -1),
              activeStepOverflow,
              introHiddenAfterConsent: body.classList.contains('questionnaire-active')
                ? getComputedStyle(document.querySelector('.intro-panel')).display === 'none'
                : true,
              consentHiddenAfterConsent: body.classList.contains('questionnaire-active')
                ? getComputedStyle(document.querySelector('.consent-panel')).display === 'none'
                : true,
            },
          };
        }
        """,
        label,
    )


async def answer_current_step(page) -> None:
    question_type = await page.locator(".wizard-step:not([hidden]) .question-card").get_attribute(
        "data-question-type"
    )
    if question_type == "textarea":
        await page.locator(".wizard-step:not([hidden]) textarea").fill("Resposta de teste visual local.")
        return

    selector = QUESTION_TYPE_SELECTORS.get(question_type or "")
    if selector:
        first = page.locator(f".wizard-step:not([{ 'hidden' }]) {selector}").first
        await first.evaluate(
            """
            (input) => {
              input.checked = true;
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """
        )
        return

    raise RuntimeError(f"Tipo de pergunta não suportado no harness: {question_type}")


async def run_viewport(browser: Browser, name: str, viewport: dict[str, Any]) -> dict[str, Any]:
    context = await browser.new_context(
        viewport={"width": viewport["width"], "height": viewport["height"]},
        is_mobile=viewport["is_mobile"],
        has_touch=viewport["is_mobile"],
        device_scale_factor=2 if viewport["is_mobile"] else 1,
    )
    page = await context.new_page()
    await page.goto(PAGE.as_uri(), wait_until="networkidle")
    await page.evaluate(
        """
        () => {
          if (window.QUESTIONARIO_CONFIG?.submission) {
            window.QUESTIONARIO_CONFIG.submission.enabled = false;
          }
        }
        """
    )
    await page.screenshot(path=OUT_DIR / f"{name}_00_consent.png", full_page=False)

    metrics: list[dict[str, Any]] = [await measure(page, f"{name}: consent screen")]

    await page.locator("#consent").check()
    await page.wait_for_selector("body.questionnaire-active")
    await page.wait_for_selector(".wizard-step:not([hidden])")
    await page.screenshot(path=OUT_DIR / f"{name}_01_primeira_pergunta.png", full_page=False)
    metrics.append(await measure(page, f"{name}: pergunta 1"))

    total_questions = await page.locator(".wizard-step").count()
    for question_index in range(total_questions):
        metrics.append(await measure(page, f"{name}: antes de responder pergunta {question_index + 1}"))
        if question_index == 3:
            await page.screenshot(path=OUT_DIR / f"{name}_02a_pergunta4_checkbox.png", full_page=False)
        if question_index == 7:
            await page.screenshot(path=OUT_DIR / f"{name}_02b_pergunta8_checkbox.png", full_page=False)
        await answer_current_step(page)
        if question_index == 4:
            await page.screenshot(path=OUT_DIR / f"{name}_02_pergunta_audio.png", full_page=False)
        if question_index < total_questions - 1:
            await page.locator("#wizard-next").click()
            await page.wait_for_timeout(720)

    metrics.append(await measure(page, f"{name}: última pergunta respondida"))
    await page.screenshot(path=OUT_DIR / f"{name}_03_ultima_pergunta.png", full_page=False)

    await page.locator("#wizard-next").click()
    await page.wait_for_selector(".wizard-feedback--overlay")
    await page.wait_for_timeout(360)  # deixa o fade-in/pop do overlay assentar antes do print
    await page.screenshot(path=OUT_DIR / f"{name}_04_confirmacao_envio.png", full_page=False)
    confirmation_ok = await page.evaluate(
        """
        () => {
          const feedback = document.querySelector('.wizard-feedback--overlay');
          const status = document.querySelector('#submission-status');
          const rect = feedback?.getBoundingClientRect();
          return Boolean(
            feedback &&
            status &&
            status.textContent.trim().length > 0 &&
            rect &&
            rect.top <= 1 &&
            rect.bottom >= window.innerHeight - 1
          );
        }
        """
    )
    await context.close()

    desktop = not viewport["is_mobile"]
    # Piso de escala efetiva por viewport: prova de que a UI abre "grande".
    # Em viewports muito curtos, caber sem corte tem prioridade sobre o piso de fonte.
    height = viewport["height"]
    if height >= 1000:
        min_font_px = 20.0
    elif not desktop:
        min_font_px = 18.0
    elif height >= 760:
        min_font_px = 18.0
    else:
        min_font_px = None
    failed = []
    if not confirmation_ok:
        failed.append(f"{name}: confirmação de envio não apareceu como overlay central")
    active_metrics = [item for item in metrics if item["activeMode"]]
    nav_gaps: list[int] = []
    for item in active_metrics:
        checks = item["checks"]
        scale = item.get("scale", {})
        if not checks["introHiddenAfterConsent"] or not checks["consentHiddenAfterConsent"]:
            failed.append(f"{item['label']}: cards iniciais continuam visíveis")
        if desktop and item["scroll"]["pageOverflow"]:
            failed.append(f"{item['label']}: página desktop exige scroll vertical")
        if desktop and checks["activeStepOverflow"]:
            failed.append(f"{item['label']}: etapa ativa desktop tem overflow interno")
        if desktop and checks.get("stepClipped"):
            failed.append(
                f"{item['label']}: alternativas cortadas — passo excede a área do viewport em {checks['viewportClipPx']}px"
            )
        if desktop and not checks["footerWithinViewport"]:
            failed.append(f"{item['label']}: rodapé saiu do viewport desktop")
        if desktop and not checks["footerAnchored"]:
            failed.append(f"{item['label']}: rodapé desktop não ficou ancorado ao fundo do viewport")
        if desktop and not checks["navWithinViewport"]:
            failed.append(f"{item['label']}: navegação saiu do viewport desktop")
        if min_font_px is not None and scale.get("bodyFontPx") is not None and scale["bodyFontPx"] < min_font_px:
            failed.append(
                f"{item['label']}: fonte base {scale['bodyFontPx']}px abaixo do piso de {min_font_px}px"
            )
        touch_floor = 40 if height >= 760 else 34
        if scale.get("optionRowHeight") is not None and scale["optionRowHeight"] < touch_floor:
            failed.append(
                f"{item['label']}: alvo de toque das opções ({scale['optionRowHeight']}px) menor que {touch_floor}px"
            )
        if scale.get("primaryButtonHeight") is not None and scale["primaryButtonHeight"] < touch_floor:
            failed.append(
                f"{item['label']}: botão de avanço ({scale['primaryButtonHeight']}px) menor que {touch_floor}px"
            )
        if desktop and scale.get("questionToNavGap") is not None:
            nav_gaps.append(scale["questionToNavGap"])

    # Gap pergunta <-> navegação deve ser constante em todas as perguntas.
    if len(nav_gaps) >= 2 and (max(nav_gaps) - min(nav_gaps)) > 2:
        failed.append(
            f"{name}: gap pergunta/navegação variou entre {min(nav_gaps)}px e {max(nav_gaps)}px (deveria ser constante)"
        )

    return {"viewport": viewport, "metrics": metrics, "failed": failed}


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    browser = await launch_browser()
    try:
        results = {}
        for name, viewport in VIEWPORTS.items():
            results[name] = await run_viewport(browser, name, viewport)
        metrics_path = OUT_DIR / "metrics.json"
        metrics_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

        failures = [failure for result in results.values() for failure in result["failed"]]
        if failures:
            print("Falhas visuais encontradas:")
            for failure in failures:
                print(f"- {failure}")
            raise SystemExit(1)

        print(f"Harness visual OK. Prints e métricas em: {OUT_DIR}")
    finally:
        playwright = getattr(browser, "_questionario_playwright", None)
        await browser.close()
        if playwright:
            await playwright.stop()


if __name__ == "__main__":
    asyncio.run(main())
