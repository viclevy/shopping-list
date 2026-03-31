import { ref } from 'vue'
import { useShoppingListStore } from '../stores/shoppingList.js'
import api from '../api.js'

const WORD_NUMBERS = {
  one: 1, two: 2, three: 3, four: 4, five: 5,
  six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15,
  sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20,
  a: 1, an: 1,
}

function parseQuantity(word) {
  if (!word) return null
  const lower = word.toLowerCase()
  if (WORD_NUMBERS[lower] !== undefined) return WORD_NUMBERS[lower]
  const num = parseFloat(lower)
  return isNaN(num) ? null : num
}

function parseCommand(text) {
  const t = text.trim().toLowerCase()

  // Check off / bought
  const checkOffMatch = t.match(/^(?:check off|bought|checked off)\s+(.+)$/i)
  if (checkOffMatch) {
    return { action: 'check_off', productName: checkOffMatch[1].trim() }
  }

  // Remove
  const removeMatch = t.match(/^remove\s+(.+)$/i)
  if (removeMatch) {
    return { action: 'remove', productName: removeMatch[1].trim() }
  }

  // Add — "add [quantity] [unit of] product name"
  const addMatch = t.match(/^add\s+(.+)$/i)
  if (addMatch) {
    const rest = addMatch[1]
    // Try to parse: "two gallons of whole milk", "3 milk", "milk"
    const qtyUnitMatch = rest.match(/^(\w+)\s+(\w+)\s+of\s+(.+)$/i)
    if (qtyUnitMatch) {
      const qty = parseQuantity(qtyUnitMatch[1])
      if (qty) {
        return { action: 'add', quantity: qty, unit: qtyUnitMatch[2], productName: qtyUnitMatch[3].trim() }
      }
    }
    // Try: "two milk" or "2 milk"
    const qtyMatch = rest.match(/^(\w+)\s+(.+)$/i)
    if (qtyMatch) {
      const qty = parseQuantity(qtyMatch[1])
      if (qty) {
        return { action: 'add', quantity: qty, unit: null, productName: qtyMatch[2].trim() }
      }
    }
    // Just product name
    return { action: 'add', quantity: 1, unit: null, productName: rest.trim() }
  }

  // Default: treat as add
  return { action: 'add', quantity: 1, unit: null, productName: t }
}

function speak(text) {
  if ('speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1.1
    speechSynthesis.speak(utterance)
  }
}

export function useVoice() {
  const isListening = ref(false)
  const transcript = ref('')
  const list = useShoppingListStore()

  let recognition = null
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (SpeechRecognition) {
    recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'

    recognition.onresult = async (event) => {
      const text = event.results[0][0].transcript
      transcript.value = text
      isListening.value = false

      try {
        const cmd = parseCommand(text)
        if (cmd.action === 'add') {
          const result = await list.addItem({
            product_name: cmd.productName,
            quantity: cmd.quantity,
            unit: cmd.unit,
          })
          speak(`Added ${cmd.productName} to the list`)
          // If the product is new (no category yet), trigger the setup dialog
          if (result?.product && !result.product.category) {
            list.pendingSetupProduct = result.product
          }
        } else if (cmd.action === 'remove') {
          const item = list.items.find(i =>
            i.product.name.toLowerCase().includes(cmd.productName.toLowerCase())
          )
          if (item) {
            await list.removeItem(item.id)
            speak(`Removed ${item.product.name} from the list`)
          } else {
            speak(`Could not find ${cmd.productName} on the list`)
          }
        } else if (cmd.action === 'check_off') {
          const item = list.items.find(i =>
            i.product.name.toLowerCase().includes(cmd.productName.toLowerCase())
          )
          if (item) {
            await list.checkOff(item.id, {})
            speak(`Checked off ${item.product.name}`)
          } else {
            speak(`Could not find ${cmd.productName} on the list`)
          }
        }
      } catch (e) {
        speak('Sorry, something went wrong')
      }

      setTimeout(() => { transcript.value = '' }, 3000)
    }

    recognition.onerror = () => {
      isListening.value = false
      transcript.value = ''
    }

    recognition.onend = () => {
      isListening.value = false
    }
  }

  function toggleListening() {
    if (!recognition) {
      alert('Speech recognition is not supported in this browser.')
      return
    }
    if (isListening.value) {
      recognition.stop()
    } else {
      isListening.value = true
      transcript.value = ''
      recognition.start()
    }
  }

  return { isListening, transcript, toggleListening }
}
