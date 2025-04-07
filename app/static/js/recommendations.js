// Get session ID from URL path (global so all functions can access)
const sessionId = window.location.pathname.split('/').pop();

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Start the page initialization
    initPage();
});

// Render skill gaps
function renderSkillGaps(skills) {
    const skillGapsContainer = document.getElementById('skill-gaps');
    skillGapsContainer.innerHTML = '';
    
    if (!skills || !Array.isArray(skills)) {
        console.error('Invalid skills data:', skills);
        return;
    }

    skills.forEach(skill => {
        const skillElement = document.createElement('div');
        skillElement.className = 'bg-[#2C2C2C] border border-[#3A3A3A] rounded-full px-4 py-2 text-sm font-medium text-[#B0B0B0]';
        skillElement.textContent = typeof skill === 'string' ? skill : skill.name || 'Unknown Skill';
        skillGapsContainer.appendChild(skillElement);
    });
}

// Render course recommendations
function renderRecommendations(recommendations) {
    const grid = document.getElementById('recommendations-grid');
    if (!grid) {
        console.error('Recommendations grid not found');
        return;
    }
    
    grid.innerHTML = '';
    
    if (recommendations.length === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'col-span-3 text-center py-10';
        noResults.innerHTML = `
            <div class="w-16 h-16 mx-auto mb-4 flex items-center justify-center bg-[#2C2C2C] rounded-full">
                <i class="ri-search-line ri-2x text-[#B0B0B0]"></i>
            </div>
            <h3 class="text-xl font-medium text-white mb-2">No courses match your filters</h3>
            <p class="text-[#B0B0B0]">Try adjusting your filter criteria to see more results.</p>
        `;
        grid.appendChild(noResults);
        return;
    }
    
    // Platform icon mapping
    const platformIcons = {
        "Udemy": "ri-slideshow-line",
        "Coursera": "ri-graduation-cap-line",
        "educative.io": "ri-book-read-line",
        "edX": "ri-open-arm-line"
    };

    recommendations.forEach(course => {
        const card = document.createElement('div');
        card.className = 'bg-[#2C2C2C] border border-[#3A3A3A] rounded-lg overflow-hidden hover:border-[#4A4A4A] transition-all';
        
        // Calculate relevance color
        let relevanceColor = 'bg-red-500';
        if (course.relevance_score >= 90) {
            relevanceColor = 'bg-green-500';
        } else if (course.relevance_score >= 80) {
            relevanceColor = 'bg-yellow-500';
        } else if (course.relevance_score >= 70) {
            relevanceColor = 'bg-orange-500';
        }

        // Get platform icon
        const iconClass = platformIcons[course.platform] || "ri-book-line";
        
        card.innerHTML = `
            <div class="p-6">
                <div class="flex items-start justify-between mb-4">
                    <div class="flex items-center">
                        <div class="w-8 h-8 flex items-center justify-center bg-[#3A3A3A] rounded-lg mr-3">
                            <i class="${iconClass} ri-lg text-white"></i>
                        </div>
                        <span class="text-[#B0B0B0] text-sm">${course.platform}</span>
                    </div>
                    <div class="flex items-center">
                        <div class="w-8 h-8 flex items-center justify-center ${relevanceColor} rounded-full">
                            <span class="text-xs font-bold text-white">${Math.round(course.relevance_score)}%</span>
                        </div>
                        <span class="ml-2 text-xs text-slate-400">Relevance</span>
                    </div>
                </div>
                
                <h3 class="text-xl font-semibold text-white mb-2">${course.title}</h3>
                
                <p class="text-[#B0B0B0] text-sm mb-4 line-clamp-3">${course.description}</p>
                
                <div class="flex flex-wrap gap-2 mb-4">
                    ${course.skills.map(skill => `
                        <span class="bg-[#3A3A3A] text-xs text-[#B0B0B0] px-2 py-1 rounded-full">${skill}</span>
                    `).join('')}
                </div>
                

                <a href="${course.url}" target="_blank" class="block w-full bg-primary hover:bg-blue-600 text-white font-medium py-2.5 px-4 rounded !rounded-button text-center transition-colors">
                    View Course
                </a>
            </div>
        `;
        
        grid.appendChild(card);
    });
}

// Show error state
function showError(code = 'UNKNOWN_ERROR', message = 'There was an error retrieving your recommendations.') {
    const grid = document.getElementById('recommendations-grid');
    const skillGapsContainer = document.getElementById('skill-gaps');
    
    // Clear skill gaps
    if (skillGapsContainer) {
        skillGapsContainer.innerHTML = '';
    }
    
    // Error message mapping
    const errorMessages = {
        'SESSION_NOT_FOUND': {
            title: 'Invalid Session',
            message: 'Please start a new assessment to get personalized recommendations.',
            action: 'Start Assessment',
            actionUrl: '/',
            icon: 'ri-error-warning-line'
        },
        'ASSESSMENT_INCOMPLETE': {
            title: 'Assessment Incomplete',
            message: 'Please complete your assessment to get personalized recommendations.',
            action: 'Resume Assessment',
            actionUrl: `/assessment/${sessionId}`,
            icon: 'ri-time-line'
        },
        'NO_RESPONSES': {
            title: 'No Responses Found',
            message: 'We couldn\'t find your assessment responses. Please try taking the assessment again.',
            action: 'Start New Assessment',
            actionUrl: '/',
            icon: 'ri-error-warning-line'
        },
        'NO_COURSES': {
            title: 'Service Temporarily Unavailable',
            message: 'Our course recommendations are currently unavailable. Please try again later.',
            action: 'Try Again',
            actionUrl: null,
            icon: 'ri-service-line'
        },
        'NO_RECOMMENDATIONS': {
            title: 'No Recommendations Found',
            message: 'We couldn\'t find any courses matching your skill gaps. Please try adjusting your filters.',
            action: 'Try Again',
            actionUrl: null,
            icon: 'ri-search-line'
        },
        'UNKNOWN_ERROR': {
            title: 'Error Loading Recommendations',
            message: message,
            action: 'Try Again',
            actionUrl: null,
            icon: 'ri-error-warning-line'
        }
    };
    
    const error = errorMessages[code] || errorMessages['UNKNOWN_ERROR'];
    
    grid.innerHTML = `
        <div class="col-span-3 text-center py-10">
            <div class="w-16 h-16 mx-auto mb-4 flex items-center justify-center bg-[#2C2C2C] rounded-full">
                <i class="${error.icon} ri-2x text-red-500"></i>
            </div>
            <h3 class="text-xl font-medium text-white mb-2">${error.title}</h3>
            <p class="text-[#B0B0B0] mb-4">${error.message}</p>
            ${error.actionUrl 
                ? `<a href="${error.actionUrl}" class="inline-block bg-[#3A3A3A] hover:bg-[#4A4A4A] text-white font-medium py-2 px-4 rounded !rounded-button transition-colors">
                    ${error.action}
                  </a>`
                : `<button onclick="initPage()" class="bg-[#3A3A3A] hover:bg-[#4A4A4A] text-white font-medium py-2 px-4 rounded !rounded-button transition-colors">
                    ${error.action}
                  </button>`
            }
        </div>
    `;
}

// Initialize the page
async function initPage() {
    try {
        console.log('Initializing page with session:', sessionId);
        const response = await fetch(`/api/recommendations/${sessionId}`);
        
        const data = await response.json();
        console.log('Received data:', data);
        
        // Handle API errors
        if (!response.ok) {
            const errorDetail = data.detail || {};
            console.error('API Error:', errorDetail);
            
            // Show appropriate error message
            showError(
                errorDetail.code || 'UNKNOWN_ERROR',
                errorDetail.message || 'Failed to load recommendations'
            );
            return;
        }
        
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid response data');
        }
        
        // Handle weak skills from the assessment
        if (Array.isArray(data.weak_skills)) {
            renderSkillGaps(data.weak_skills);
        } else {
            console.error('Invalid weak_skills data:', data.weak_skills);
            throw new Error('Invalid weak skills data');
        }
        
        // Handle course recommendations
        if (Array.isArray(data.recommendations)) {
            renderRecommendations(data.recommendations);
        } else {
            console.error('Invalid recommendations data:', data.recommendations);
            throw new Error('Invalid recommendations data');
        }
    } catch (error) {
        console.error('Error in initPage:', error);
        showError('UNKNOWN_ERROR', error.message);
    }
}

