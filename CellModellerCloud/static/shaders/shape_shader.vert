#pragma vscode_glsllint_stage : vert

layout(location = 0) in vec3 a_Position;

uniform mat4 u_ViewMatrix;
uniform mat4 u_ProjectionMatrix;

uniform mat4 u_ModelMatrix;

void main() {
	gl_Position = u_ProjectionMatrix * u_ViewMatrix * u_ModelMatrix * vec4(a_Position, 1.0);
}