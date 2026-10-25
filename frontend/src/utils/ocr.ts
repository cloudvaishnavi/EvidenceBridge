import Tesseract from 'tesseract.js'

export interface OcrResult {
  text: string
  confidence: number
  isLowQuality: boolean
  warningMessage?: string
}

export type OcrProgressCallback = (progress: number, status: string) => void

/**
 * Extracts text from an image (File, Blob, or base64/object URL) using Tesseract.js.
 * Handles progress callbacks and quality evaluation.
 */
export async function extractTextFromImage(
  imageSource: File | Blob | string,
  onProgress?: OcrProgressCallback
): Promise<OcrResult> {
  try {
    const result = await Tesseract.recognize(
      imageSource,
      'eng',
      {
        logger: (m) => {
          if (m && typeof m.progress === 'number') {
            const pct = Math.round(m.progress * 100)
            const statusText = m.status === 'recognizing text' 
              ? `Reading image... ${pct}%` 
              : (m.status ? `${m.status.charAt(0).toUpperCase() + m.status.slice(1)}...` : 'Processing...')
            onProgress?.(pct, statusText)
          }
        },
      }
    )

    const rawText = (result.data?.text || '').trim()
    const confidence = typeof result.data?.confidence === 'number' ? result.data.confidence : 0

    // Check for empty or very low quality OCR
    // 1. Text is virtually empty (< 10 non-whitespace chars)
    // 2. Average confidence is below 55%
    // 3. Text has very few actual words (mostly punctuation/noise)
    const words = rawText.split(/\s+/).filter((w) => w.length > 1)
    const isVeryShort = rawText.replace(/\s+/g, '').length < 10
    const isLowConfidence = confidence < 55
    const hasFewWords = words.length < 3

    const isLowQuality = isVeryShort || isLowConfidence || hasFewWords

    let warningMessage: string | undefined = undefined
    if (isLowQuality) {
      warningMessage = 'Some parts of the image could not be read clearly. Please check the text below or type the missing information.'
    }

    return {
      text: rawText,
      confidence,
      isLowQuality,
      warningMessage,
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to process image OCR'
    console.error('OCR processing error:', err)
    return {
      text: '',
      confidence: 0,
      isLowQuality: true,
      warningMessage: `OCR processing encountered an issue: ${message}. You can manually type or paste the bill details.`,
    }
  }
}
