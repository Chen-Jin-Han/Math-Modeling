-- Word cannot reliably render PDF figure payloads.  Keep the evidence-bound
-- Markdown unchanged and select the registered 450-DPI PNG sibling only for
-- the DOCX conversion.
function Image(image)
  image.src = image.src:gsub("%.pdf$", ".png")
  return image
end

-- Claim anchors are machine-readable manuscript evidence.  They remain in the
-- registered Markdown but must never leak into the human-facing companion
-- document.
function Str(element)
  element.text = element.text:gsub("%[claim:[^%]]+%]", "")
  if element.text == "" then
    return {}
  end
  return element
end
