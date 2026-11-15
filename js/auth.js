const role = new URLSearchParams(location.search).get('role');
const roleTitle = document.getElementById('roleTitle');
const roleDescription = document.getElementById('roleDescription');
const organizationFields = document.getElementById('organizationFields');
const message = document.getElementById('authMessage');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');

if (!['individual', 'organization'].includes(role)) {
  location.replace('account-type.html');
} else {
  const isOrganization = role === 'organization';
  roleTitle.textContent = isOrganization ? 'Compte organisation' : 'Compte individuel';
  roleDescription.textContent = isOrganization
    ? 'Connectez-vous ou inscrivez votre association, hôtel ou restaurant.'
    : 'Connectez-vous ou inscrivez-vous pour gérer vos aliments.';
  organizationFields.hidden = !isOrganization;
  organizationFields.querySelectorAll('input, select').forEach(field => {
    field.disabled = !isOrganization;
    field.required = isOrganization;
  });
}

document.querySelectorAll('.auth-tabs button').forEach(button => {
  button.addEventListener('click', () => {
    const showLogin = button.dataset.mode === 'login';
    loginForm.hidden = !showLogin;
    registerForm.hidden = showLogin;
    document.querySelectorAll('.auth-tabs button').forEach(tab => {
      tab.setAttribute('aria-selected', String(tab === button));
    });
    message.textContent = '';
    message.className = 'msg';
  });
});

async function envoyer(url, donnees) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(donnees)
  });
  let result = {};
  try { result = await response.json(); } catch (e) {}
  if (!response.ok) throw new Error(result.error || 'Une erreur est survenue.');
  location.assign(result.redirect);
}

loginForm.addEventListener('submit', async event => {
  event.preventDefault();
  message.textContent = '';
  message.className = 'msg';
  try {
    await envoyer('/api/login', {
      role,
      email: document.getElementById('loginEmail').value,
      password: document.getElementById('loginPassword').value
    });
  } catch (error) {
    message.textContent = error.message;
    message.className = 'msg err';
  }
});

registerForm.addEventListener('submit', async event => {
  event.preventDefault();
  message.textContent = '';
  message.className = 'msg';
  const donnees = {
    role,
    email: document.getElementById('registerEmail').value,
    password: document.getElementById('registerPassword').value
  };
  if (role === 'organization') {
    donnees.name = document.getElementById('organizationName').value;
    donnees.organization_type = document.getElementById('organizationType').value;
    donnees.address = document.getElementById('organizationAddress').value;
    donnees.phone = document.getElementById('organizationPhone').value;
  }
  try {
    await envoyer('/api/register', donnees);
  } catch (error) {
    message.textContent = error.message;
    message.className = 'msg err';
  }
});
