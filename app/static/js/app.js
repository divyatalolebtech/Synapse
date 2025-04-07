let currentSession = null;
let currentQuestion = null;
let retryCount = 0;

// Initialize session from URL
function initializeSession() {
    const pathParts = window.location.pathname.split('/');
    const sessionId = pathParts[pathParts.length - 1];
    if (sessionId && pathParts[1] === 'assessment') {
        if (!/^[a-zA-Z0-9-_]+$/.test(sessionId)) {  
            console.error('Invalid session ID format');
            updateQuestionText('Invalid session ID. Please start a new assessment.');
            return;
        }
        currentSession = { id: sessionId };
        console.log('Session initialized:', currentSession);
        getNextQuestion(); 
    }
}

// Get next question
async function getNextQuestion() {
    if (!currentSession || !currentSession.id) {
        console.error('No current session or invalid session ID');
        updateQuestionText('No active assessment session. Please start a new assessment.');
        return;
    }
    
    try {
        console.log('Fetching next question for session:', currentSession.id);
        const response = await fetch(`/questions/${currentSession.id}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        // Handle 404 (no more questions) and 400 (assessment completed) separately
        if (response.status === 404 || response.status === 400) {
            console.log('Assessment complete');
            updateQuestionText('Assessment complete! Redirecting to results...');
            // Redirect to results page after a short delay
            setTimeout(() => {
                window.location.href = `/results/${currentSession.id}`;
            }, 2000);
            return;
        }
        
        // For other error responses
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
        }
        
        // Try to parse the response as JSON
        let data;
        try {
            data = await response.json();
        } catch (e) {
            console.error('JSON parse error:', e);
            throw new Error('Invalid response format');
        }
        
        if (!data || !data.text) {
            console.error('Invalid question data:', data);
            throw new Error('Invalid question data received: missing required fields');
        }
        
        // Reset retry counter on successful question fetch
        retryCount = 0;
        
        // Update current question and display it
        currentQuestion = data;
        displayQuestion(data);
        
        // Update progress if available
        if (data.progress) {
            updateProgress(data.progress);
        }
        
        // Enable/disable navigation buttons
        const nextButton = document.getElementById('nextButton');
        if (nextButton) {
            nextButton.disabled = true; // Will be enabled when user selects an answer
        }
        
        return data;
    } catch (error) {
        // Log detailed error information
        console.error('Error getting question:', {
            message: error.message,
            stack: error.stack,
            sessionId: currentSession?.id
        });
        
        // Implement exponential backoff for retries
        if (retryCount < 3) {  // Maximum 3 retries
            const delay = Math.pow(2, retryCount) * 1000;  // Exponential backoff: 1s, 2s, 4s
            console.log(`Retry ${retryCount + 1}/3 in ${delay/1000} seconds...`);
            retryCount++;
            setTimeout(() => {
                getNextQuestion();
            }, delay);
        } else {
            updateQuestionText('Failed to load question after multiple attempts. Please refresh the page or start a new assessment.');
        }
        
        const nextButton = document.getElementById('nextButton');
        if (nextButton) {
            nextButton.disabled = false;
        }
    }
}

// Helper function to safely update question text
function updateQuestionText(text) {
    const questionText = document.getElementById('questionText');
    if (questionText) {
        questionText.textContent = text;
    } else {
        console.warn('Question text element not found');
    }
}

// Helper function to update progress
function updateProgress(progress) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('currentQuestion');
    const totalText = document.getElementById('totalQuestions');
    const currentSkill = document.getElementById('currentSkill');
    
    if (progressBar) {
        progressBar.style.width = `${progress.percentage}%`;
        progressBar.setAttribute('aria-valuenow', progress.percentage);
    }
    
    if (progressText && totalText) {
        progressText.textContent = progress.completed;
        totalText.textContent = progress.total;
    }
    
    // Update skill dimensions if available
    // Update radar chart if available
    if (progress.skill_scores && progress.skill_scores.length > 0) {
        updateRadarChart(progress.skill_scores);
        
        const skillDimensions = document.getElementById('skillDimensions');
        if (skillDimensions) {
            skillDimensions.innerHTML = progress.skill_scores.map(skill => `
                <div class="mb-4">
                    <div class="flex justify-between mb-2">
                        <span class="text-sm text-[#B0B0B0]">${formatLabel(skill.dimension)}</span>
                        <span class="text-sm font-medium">${skill.level}</span>
                    </div>
                    <div class="w-full bg-[#333333] rounded-full h-2">
                        <div class="bg-primary h-2 rounded-full" style="width: ${Math.min(skill.score, 100)}%" title="${Math.round(skill.score)}%"></div>
                    </div>
                </div>
            `).join('');
        }
    }
}

// Display question
function displayQuestion(question) {
    const questionText = document.getElementById('questionText');
    const optionsContainer = document.getElementById('optionsContainer');
    const currentSkill = document.getElementById('currentSkill');
    
    if (!questionText || !optionsContainer) {
        console.error('Required DOM elements not found');
        return;
    }
    
    // Update current skill dimension
    if (currentSkill && question.skill_dimension) {
        currentSkill.innerHTML = `<span class="text-white">Current Skill:</span> <span class="text-primary font-medium">${formatLabel(question.skill_dimension)}</span>`;
    }
    
    questionText.textContent = question.text;
    
    optionsContainer.innerHTML = '';
    
    if (question.options) {
        Object.entries(question.options).forEach(([key, value]) => {
            const label = document.createElement('label');
            label.className = 'flex items-center space-x-2 p-3 bg-[#1E1E1E] rounded-lg cursor-pointer hover:bg-[#2A2A2A]';
            
            const input = document.createElement('input');
            input.type = 'radio';
            input.name = 'answer';
            input.value = key;
            input.className = 'form-radio text-primary';
            
            const span = document.createElement('span');
            span.textContent = value;
            span.className = 'text-white';
            
            label.appendChild(input);
            label.appendChild(span);
            optionsContainer.appendChild(label);
            
            input.addEventListener('change', () => {
                document.getElementById('nextButton').disabled = false;
            });
        });
    }
}

// Start assessment
async function startAssessment(assessmentId) {
    try {
        const role = assessmentId.replace('-', '_');
        console.log('Starting assessment for role:', role);
        
        const response = await fetch('/assessments/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ role })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Assessment started:', data);
        
        if (!data || !data.id) {
            throw new Error('Invalid response data: missing session ID');
        }
        
        window.location.href = `/assessment/${data.id}`;
    } catch (error) {
        console.error('Error starting assessment:', error);
        alert('Failed to start assessment: ' + error.message);
    }
}

// Initialize when the page loads
// Initialize and update radar chart
// Format dimension label for display
function formatLabel(dim) {
    return dim
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

function updateRadarChart(skillScores) {
    if (!radarChart) {
        radarChart = initializeEmptyRadarChart();
        if (!radarChart) return;
    }

    // If no skill scores yet, initialize with empty values
    if (!skillScores || skillScores.length === 0) {
        // We don't want to update the chart with no data
        return;
    }

    const dimensions = skillScores.map(s => s.dimension);
    // Backend already provides scores in 0-100 range, no need to multiply
    const scores = skillScores.map(s => Math.min(s.score, 100));

    const option = {
        tooltip: {
            trigger: 'item',
            formatter: (params) => {
                const value = params.value[params.dimensionIndex];
                const dimension = formatLabel(dimensions[params.dimensionIndex]);
                return `${dimension}: ${Math.round(value)}%`;
            }
        },
        radar: {
            indicator: dimensions.map(dim => ({
                name: formatLabel(dim),
                max: 100
            })),
            splitArea: {
                show: true,
                areaStyle: {
                    color: ['rgba(50,50,50,0.3)', 'rgba(40,40,40,0.3)', 'rgba(30,30,30,0.3)', 'rgba(20,20,20,0.3)']
                }
            },
            axisLine: { lineStyle: { color: '#666' } },
            splitLine: { lineStyle: { color: '#666' } },
            name: { textStyle: { color: '#B0B0B0' } }
        },
        series: [{
            type: 'radar',
            data: [{
                value: scores,
                name: 'Skills',
                areaStyle: { color: 'rgba(0,122,255,0.2)' },
                lineStyle: { color: '#007AFF' },
                itemStyle: { color: '#007AFF' }
            }]
        }]
    };

    radarChart.setOption(option, true);  // true forces a complete refresh
}

// Initialize empty radar chart
function initializeEmptyRadarChart() {
    const chartDom = document.getElementById('skillRadarChart');
    if (!chartDom) return null;
    return echarts.init(chartDom);
}

// Keep track of the chart instance
let radarChart = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log('Page loaded, initializing session...');
    // Initialize empty radar chart
    radarChart = initializeEmptyRadarChart();
    initializeSession();
    
    const nextButton = document.getElementById('nextButton');
    if (nextButton) {
        nextButton.addEventListener('click', async () => {
            const selectedAnswer = document.querySelector('input[name="answer"]:checked');
            if (selectedAnswer && currentQuestion) {
                nextButton.disabled = true;
                try {
                    console.log('Submitting answer:', {
                        question_id: currentQuestion.id,
                        response: selectedAnswer.value
                    });
                    
                    const response = await fetch(`/responses/${currentSession.id}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        body: JSON.stringify({
                            question_id: currentQuestion.id,
                            response: selectedAnswer.value
                        })
                    });
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(`Failed to submit answer: ${errorText}`);
                    }
                    
                    const data = await response.json();
                    console.log('Answer submitted successfully:', data);
                    
                    if (data.next_question_available) {
                        await getNextQuestion();
                    } else {
                        console.log('Assessment complete');
                        updateQuestionText('Assessment complete! Redirecting to results...');
                        setTimeout(() => {
                            window.location.href = `/results/${currentSession.id}`;
                        }, 2000);
                    }
                } catch (error) {
                    console.error('Error submitting answer:', error);
                    nextButton.disabled = false;
                    alert('Failed to submit answer: ' + error.message);
                }
            }
        });
    }
});
