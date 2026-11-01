export async function fetchPatients() {
    const response = await fetch("https://jsonplaceholder.typicode.com/users");
    return response.json();
  }