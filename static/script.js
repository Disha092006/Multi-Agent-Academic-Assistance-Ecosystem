// --- Homepage: 4-tab mode switching (Ask, Notes, Quiz, Revision) ---
const modeTabs = document.querySelectorAll('.mode-tab');
const generateModeCard = document.getElementById('generate-mode-card');
const askModeCard = document.getElementById('ask-mode-card');
const hiddenNotes = document.getElementById('hidden-notes');
const hiddenQuiz = document.getElementById('hidden-quiz');
const hiddenRevision = document.getElementById('hidden-revision');
const generateBtnLabel = document.getElementById('generate-btn-label');
const generateModeDescription = document.getElementById('generate-mode-description');

const modeConfig = {
  notes: {
    label: 'Generate Notes',
    description: 'Generates structured notes from your document.'
  },
  quiz: {
    label: 'Generate Quiz',
    description: 'Generates an interactive multiple-choice quiz with scoring.'
  },
  revision: {
    label: 'Generate Revision Plan',
    description: 'Generates a 2-day study plan (uses Notes + Quiz internally as input).'
  }
};

if (modeTabs.length > 0) {
  modeTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      modeTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const mode = tab.getAttribute('data-mode');

      if (mode === 'ask') {
        generateModeCard.style.display = 'none';
        askModeCard.style.display = 'block';
        return;
      }

      askModeCard.style.display = 'none';
      generateModeCard.style.display = 'block';

      hiddenNotes.checked = (mode === 'notes');
      hiddenQuiz.checked = (mode === 'quiz');
      hiddenRevision.checked = (mode === 'revision');

      const config = modeConfig[mode];
      generateBtnLabel.textContent = config.label;
      generateModeDescription.textContent = config.description;
    });
  });
}

// --- Homepage: Ask-mode dropzone ---
const askDropzone = document.getElementById('ask-dropzone');
const qaFileInput = document.getElementById('qa_file');
const askDropzoneLabel = document.getElementById('ask-dropzone-label');

if (askDropzone && qaFileInput) {
  askDropzone.addEventListener('click', () => qaFileInput.click());

  qaFileInput.addEventListener('change', () => {
    if (qaFileInput.files.length > 0) {
      askDropzoneLabel.textContent = qaFileInput.files[0].name;
    }
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    askDropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      askDropzone.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    askDropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      askDropzone.classList.remove('drag-over');
    });
  });

  askDropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      qaFileInput.files = files;
      askDropzoneLabel.textContent = files[0].name;
    }
  });
}

// --- Upload page: dropzone + loading overlay ---
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('pdf_file');
const dropzoneLabel = document.getElementById('dropzone-label');
const uploadForm = document.getElementById('upload-form');
const loadingOverlay = document.getElementById('loading-overlay');
const loadingMessage = document.getElementById('loading-message');

if (dropzone && fileInput) {
  dropzone.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      dropzoneLabel.textContent = fileInput.files[0].name;
    }
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      fileInput.files = files;
      dropzoneLabel.textContent = files[0].name;
    }
  });
}

if (uploadForm) {
  uploadForm.addEventListener('submit', (e) => {
    if (!fileInput.files || fileInput.files.length === 0) {
      return;
    }
    loadingOverlay.classList.add('visible');

    const loadingSteps = [];
    const notesChecked = document.querySelector('input[name="notes"]').checked;
    const quizChecked = document.querySelector('input[name="quiz"]').checked;
    const revisionChecked = document.querySelector('input[name="revision"]').checked;

    if (notesChecked || revisionChecked) {
      loadingSteps.push("Notes Agent is reading your document...");
      loadingSteps.push("Notes Agent is writing structured notes...");
    }
    if (quizChecked || revisionChecked) {
      loadingSteps.push("Quiz Agent is designing questions...");
    }
    if (revisionChecked) {
      loadingSteps.push("Revision Agent is building your study plan...");
    }
    loadingSteps.push("Almost done, finalizing results...");

    let step = 0;
    loadingMessage.textContent = loadingSteps[0];
    setInterval(() => {
      step = (step + 1) % loadingSteps.length;
      loadingMessage.textContent = loadingSteps[step];
    }, 8000);
  });
}

// --- Results page: tab switching ---
const tabButtons = document.querySelectorAll('.tab-btn');
tabButtons.forEach(button => {
  button.addEventListener('click', () => {
    const targetTab = button.getAttribute('data-tab');
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    button.classList.add('active');
    document.getElementById('tab-' + targetTab).classList.add('active');
  });
});

// --- Results page: interactive quiz scoring ---
const submitQuizBtn = document.getElementById('submit-quiz-btn');
if (submitQuizBtn) {
  submitQuizBtn.addEventListener('click', () => {
    const questionBlocks = document.querySelectorAll('.quiz-question');
    let correctCount = 0;
    let wrongAnswers = [];
    let weakTopics = new Set();
    let unanswered = 0;

    questionBlocks.forEach((block, index) => {
      const correctIndex = parseInt(block.getAttribute('data-correct-index'), 10);
      const topic = block.getAttribute('data-topic');
      const selected = block.querySelector('input[type="radio"]:checked');
      const questionText = block.querySelector('.quiz-question-text').textContent;
      const options = block.querySelectorAll('.quiz-option');

      // Reset styling
      options.forEach(opt => opt.classList.remove('correct-option', 'wrong-option'));

      if (!selected) {
        unanswered++;
        weakTopics.add(topic);
        // Highlight the correct answer since they skipped it
        options[correctIndex].classList.add('correct-option');
        wrongAnswers.push({
          question: questionText,
          correctAnswer: options[correctIndex].querySelector('span').textContent,
          yourAnswer: "(not answered)"
        });
        return;
      }

      const selectedIndex = parseInt(selected.value, 10);

      if (selectedIndex === correctIndex) {
        correctCount++;
        options[correctIndex].classList.add('correct-option');
      } else {
        weakTopics.add(topic);
        options[correctIndex].classList.add('correct-option');
        options[selectedIndex].classList.add('wrong-option');
        wrongAnswers.push({
          question: questionText,
          correctAnswer: options[correctIndex].querySelector('span').textContent,
          yourAnswer: options[selectedIndex].querySelector('span').textContent
        });
      }
    });

    const total = questionBlocks.length;
    const percent = total > 0 ? Math.round((correctCount / total) * 100) : 0;

    document.getElementById('score-number').textContent = `${correctCount}/${total}`;
    document.getElementById('score-percent').textContent = `${percent}%`;

    const weakTopicsEl = document.getElementById('weak-topics');
    if (weakTopics.size > 0) {
      weakTopicsEl.innerHTML = '<h4>Topics to review:</h4><ul>' +
        Array.from(weakTopics).map(t => `<li>${t}</li>`).join('') +
        '</ul>';
    } else {
      weakTopicsEl.innerHTML = '<p class="perfect-score-msg">Great job - no weak topics found!</p>';
    }

    const wrongListEl = document.getElementById('wrong-answers-list');
    if (wrongAnswers.length > 0) {
      wrongListEl.innerHTML = '<h4>Review your mistakes:</h4>' +
        wrongAnswers.map(w => `
          <div class="wrong-answer-item">
            <p class="wrong-q">${w.question}</p>
            <p class="wrong-your">Your answer: ${w.yourAnswer}</p>
            <p class="wrong-correct">Correct answer: ${w.correctAnswer}</p>
          </div>
        `).join('');
    } else {
      wrongListEl.innerHTML = '';
    }

    document.getElementById('quiz-results').style.display = 'block';
    submitQuizBtn.disabled = true;
    document.getElementById('quiz-results').scrollIntoView({ behavior: 'smooth' });
  });
}

// --- Results page: Ask a Question feature ---
const askBtn = document.getElementById('ask-btn');
if (askBtn) {
  const questionInput = document.getElementById('question-input');
  const chatLog = document.getElementById('chat-log');
  const documentId = document.getElementById('document-id').value;

  function addChatBubble(text, sender) {
    const bubble = document.createElement('div');
    bubble.className = sender === 'user' ? 'chat-bubble chat-user' : 'chat-bubble chat-ai';
    bubble.textContent = text;
    chatLog.appendChild(bubble);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  async function sendQuestion() {
    const question = questionInput.value.trim();
    if (!question) return;

    const modelSelect = document.getElementById('ask_model_choice');
    const modelChoice = modelSelect ? modelSelect.value : 'llama';

    addChatBubble(question, 'user');
    questionInput.value = '';
    askBtn.disabled = true;
    addChatBubble('Thinking...', 'ai');

    try {
      const response = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: documentId, question: question, model_choice: modelChoice })
      });
      const data = await response.json();

      chatLog.removeChild(chatLog.lastChild);

      if (data.error) {
        addChatBubble('Error: ' + data.error, 'ai');
      } else {
        addChatBubble(data.answer, 'ai');
      }
    } catch (error) {
      chatLog.removeChild(chatLog.lastChild);
      addChatBubble('Something went wrong. Please try again.', 'ai');
    }

    askBtn.disabled = false;
  }

  askBtn.addEventListener('click', sendQuestion);
  questionInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendQuestion();
  });
}